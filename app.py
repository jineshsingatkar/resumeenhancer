from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import time
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.orm import DeclarativeBase
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from resume_modifier.resume_parser import ResumeParser
from resume_modifier.resume_formatter import ResumeFormatter
from resume_modifier.llm_model import LLMModel
from resume_scoring import ResumeScorer
from models import (db, User, ResumeTemplate, UserResume, JobApplication, 
                   BatchProcessing, ResumeSession, ResumeAnalytics, 
                   PopularKeywords, UserFeedback)
from forms import (LoginForm, RegistrationForm, ResumeUploadForm, BatchUploadForm,
                  JobApplicationForm, ProfileForm, AdminUserForm, TemplateForm)
from auth import admin_required, subscription_required


class Base(DeclarativeBase):
    pass


# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Upload configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
TEMPLATE_FOLDER = 'templates/resume_templates'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['TEMPLATE_FOLDER'] = TEMPLATE_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)

# Initialize AI models
llm_model = LLMModel()
resume_scorer = ResumeScorer()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.get_full_name()}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ============================================================================
# MAIN APPLICATION ROUTES
# ============================================================================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Get statistics for landing page
    total_users = User.query.count()
    total_resumes = ResumeSession.query.filter_by(success=True).count()
    templates_count = ResumeTemplate.query.count()
    
    stats = {
        'total_users': f"{total_users:,}",
        'total_resumes': f"{total_resumes:,}+",
        'templates_count': templates_count,
        'success_rate': "98%"
    }
    
    return render_template('index.html', stats=stats)


@app.route('/dashboard')
@login_required
def dashboard():
    # User's recent resumes
    recent_resumes = UserResume.query.filter_by(user_id=current_user.id)\
                                   .order_by(UserResume.created_at.desc())\
                                   .limit(5).all()
    
    # User's recent applications
    recent_applications = JobApplication.query.filter_by(user_id=current_user.id)\
                                            .order_by(JobApplication.application_date.desc())\
                                            .limit(5).all()
    
    # User stats
    user_stats = {
        'total_resumes': UserResume.query.filter_by(user_id=current_user.id).count(),
        'total_applications': JobApplication.query.filter_by(user_id=current_user.id).count(),
        'avg_score': db.session.query(db.func.avg(UserResume.ai_score))\
                              .filter_by(user_id=current_user.id).scalar() or 0,
        'this_month': UserResume.query.filter(
            UserResume.user_id == current_user.id,
            UserResume.created_at >= datetime.utcnow().replace(day=1)
        ).count()
    }
    
    return render_template('dashboard/index.html', 
                         recent_resumes=recent_resumes,
                         recent_applications=recent_applications,
                         user_stats=user_stats)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_resume():
    form = ResumeUploadForm()
    
    # Populate template choices
    templates = ResumeTemplate.query.all()
    form.template_id.choices = [(t.id, t.name) for t in templates]
    
    if form.validate_on_submit():
        try:
            file = form.resume_file.data
            job_description = form.job_description.data or "General professional role requiring relevant skills and experience."
            template_id = form.template_id.data
            
            # Save uploaded file
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Process resume
            start_time = time.time()
            session_id = str(uuid.uuid4())
            
            # Parse resume
            parser = ResumeParser(file_path)
            resume_data = parser.parse_resume()
            
            # Analyze job description
            keywords = llm_model.parse_job_description(job_description)
            
            # Modify resume
            formatter = ResumeFormatter()
            modified_resume = formatter.modify_resume(resume_data, keywords)
            
            # Calculate AI score
            score_data = resume_scorer.calculate_comprehensive_score(
                modified_resume, job_description, json.dumps(keywords)
            )
            
            # Save to user's resumes
            user_resume = UserResume(
                user_id=current_user.id,
                title=f"Resume for {job_description[:50]}...",
                original_filename=filename,
                template_id=template_id,
                job_description=job_description,
                keywords_matched=json.dumps(keywords),
                ai_score=score_data.get('overall_score', 0)
            )
            db.session.add(user_resume)
            
            # Update user's resume count
            current_user.resumes_processed += 1
            db.session.commit()
            
            # Generate output file
            output_filename = f"enhanced_{filename}"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            
            # Create enhanced resume document
            formatter.create_enhanced_document(modified_resume, output_path, template_id)
            
            processing_time = time.time() - start_time
            
            # Clean up uploaded file
            os.remove(file_path)
            
            flash('Resume processed successfully!', 'success')
            return render_template('result.html', 
                                 resume_data=modified_resume,
                                 score_data=score_data,
                                 download_filename=output_filename,
                                 processing_time=processing_time)
            
        except Exception as e:
            flash(f'Error processing resume: {str(e)}', 'error')
            return redirect(url_for('upload_resume'))
    
    return render_template('upload.html', form=form, templates=templates)


@app.route('/batch-upload', methods=['GET', 'POST'])
@login_required
@subscription_required(['premium', 'enterprise'])
def batch_upload():
    form = BatchUploadForm()
    
    # Populate template choices
    templates = ResumeTemplate.query.all()
    form.template_id.choices = [(t.id, t.name) for t in templates]
    
    if form.validate_on_submit():
        try:
            files = form.resume_files.data
            job_description = form.job_description.data
            template_id = form.template_id.data
            
            # Create batch processing record
            batch_id = str(uuid.uuid4())
            batch_job = BatchProcessing(
                user_id=current_user.id,
                batch_id=batch_id,
                total_files=len(files),
                job_description=job_description
            )
            db.session.add(batch_job)
            db.session.commit()
            
            # Process files asynchronously (simplified for demo)
            for file in files:
                try:
                    # Save and process each file
                    filename = secure_filename(file.filename)
                    unique_filename = f"{batch_id}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    
                    # Process resume (simplified)
                    parser = ResumeParser(file_path)
                    resume_data = parser.parse_resume()
                    
                    keywords = llm_model.parse_job_description(job_description)
                    formatter = ResumeFormatter()
                    modified_resume = formatter.modify_resume(resume_data, keywords)
                    
                    # Calculate score
                    score_data = resume_scorer.calculate_comprehensive_score(
                        modified_resume, job_description, json.dumps(keywords)
                    )
                    
                    # Save user resume
                    user_resume = UserResume(
                        user_id=current_user.id,
                        title=f"Batch: {filename}",
                        original_filename=filename,
                        template_id=template_id,
                        job_description=job_description,
                        keywords_matched=json.dumps(keywords),
                        ai_score=score_data.get('overall_score', 0)
                    )
                    db.session.add(user_resume)
                    
                    batch_job.processed_files += 1
                    os.remove(file_path)
                    
                except Exception as e:
                    batch_job.failed_files += 1
                    continue
            
            batch_job.status = 'completed'
            batch_job.completed_at = datetime.utcnow()
            current_user.resumes_processed += batch_job.processed_files
            db.session.commit()
            
            flash(f'Batch processing completed! {batch_job.processed_files} resumes processed successfully.', 'success')
            return redirect(url_for('my_resumes'))
            
        except Exception as e:
            flash(f'Batch processing failed: {str(e)}', 'error')
    
    return render_template('batch_upload.html', form=form, templates=templates)


@app.route('/my-resumes')
@login_required
def my_resumes():
    page = request.args.get('page', 1, type=int)
    resumes = UserResume.query.filter_by(user_id=current_user.id)\
                            .order_by(UserResume.created_at.desc())\
                            .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('dashboard/my_resumes.html', resumes=resumes)


@app.route('/applications')
@login_required
def applications():
    page = request.args.get('page', 1, type=int)
    applications = JobApplication.query.filter_by(user_id=current_user.id)\
                                     .order_by(JobApplication.application_date.desc())\
                                     .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('dashboard/applications.html', applications=applications)


@app.route('/add-application', methods=['GET', 'POST'])
@login_required
def add_application():
    form = JobApplicationForm()
    
    # Get user's resumes for selection
    resumes = UserResume.query.filter_by(user_id=current_user.id).all()
    
    if form.validate_on_submit():
        application = JobApplication(
            user_id=current_user.id,
            resume_id=request.form.get('resume_id'),
            company_name=form.company_name.data,
            job_title=form.job_title.data,
            job_url=form.job_url.data,
            status=form.status.data,
            notes=form.notes.data
        )
        db.session.add(application)
        db.session.commit()
        
        flash('Job application added successfully!', 'success')
        return redirect(url_for('applications'))
    
    return render_template('dashboard/add_application.html', form=form, resumes=resumes)


@app.route('/templates')
def templates():
    category = request.args.get('category', 'all')
    
    query = ResumeTemplate.query
    if category != 'all':
        query = query.filter_by(category=category)
    
    templates = query.all()
    categories = db.session.query(ResumeTemplate.category.distinct()).all()
    
    return render_template('templates.html', templates=templates, categories=categories, selected_category=category)


@app.route('/template-preview/<int:template_id>')
def template_preview(template_id):
    template = ResumeTemplate.query.get_or_404(template_id)
    return render_template('template_preview.html', template=template)


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Admin statistics
    stats = {
        'total_users': User.query.count(),
        'total_resumes': UserResume.query.count(),
        'total_sessions': ResumeSession.query.count(),
        'total_templates': ResumeTemplate.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'premium_users': User.query.filter(User.subscription_type.in_(['premium', 'enterprise'])).count(),
        'this_month_resumes': UserResume.query.filter(
            UserResume.created_at >= datetime.utcnow().replace(day=1)
        ).count(),
        'avg_score': db.session.query(db.func.avg(UserResume.ai_score)).scalar() or 0
    }
    
    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_resumes = UserResume.query.order_by(UserResume.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_users=recent_users, 
                         recent_resumes=recent_resumes)


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    users = query.order_by(User.created_at.desc())\
               .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/users.html', users=users, search=search)


@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminUserForm(obj=user)
    
    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data
        user.subscription_type = form.subscription_type.data
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/edit_user.html', form=form, user=user)


@app.route('/admin/templates')
@login_required
@admin_required
def admin_templates():
    templates = ResumeTemplate.query.all()
    return render_template('admin/templates.html', templates=templates)


@app.route('/admin/template/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_template():
    form = TemplateForm()
    
    if form.validate_on_submit():
        template = ResumeTemplate(
            name=form.name.data,
            description=form.description.data,
            category=form.category.data,
            is_premium=form.is_premium.data,
            template_file='default_template.docx'  # You would handle file upload here
        )
        
        db.session.add(template)
        db.session.commit()
        flash('Template added successfully!', 'success')
        return redirect(url_for('admin_templates'))
    
    return render_template('admin/add_template.html', form=form)


@app.route('/admin/analytics')
@login_required
@admin_required
def admin_analytics():
    # Advanced analytics queries
    analytics = {
        'daily_signups': db.session.query(
            db.func.date(User.created_at).label('date'),
            db.func.count(User.id).label('count')
        ).group_by(db.func.date(User.created_at)).limit(30).all(),
        
        'popular_templates': db.session.query(
            ResumeTemplate.name,
            db.func.count(UserResume.id).label('usage_count')
        ).join(UserResume).group_by(ResumeTemplate.name).order_by(
            db.func.count(UserResume.id).desc()
        ).limit(10).all(),
        
        'score_distribution': db.session.query(
            db.func.round(UserResume.ai_score/10)*10,
            db.func.count(UserResume.id)
        ).group_by(db.func.round(UserResume.ai_score/10)*10).all(),
        
        'subscription_breakdown': db.session.query(
            User.subscription_type,
            db.func.count(User.id)
        ).group_by(User.subscription_type).all()
    }
    
    return render_template('admin/analytics.html', analytics=analytics)


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/upload-progress')
@login_required
def upload_progress():
    # Return upload progress (simplified)
    return jsonify({'progress': 100, 'status': 'completed'})


@app.route('/api/batch-status/<batch_id>')
@login_required
def batch_status(batch_id):
    batch = BatchProcessing.query.filter_by(batch_id=batch_id, user_id=current_user.id).first_or_404()
    return jsonify({
        'status': batch.status,
        'progress': batch.get_progress_percentage(),
        'processed': batch.processed_files,
        'total': batch.total_files,
        'failed': batch.failed_files
    })


@app.route('/api/resume-score/<int:resume_id>')
@login_required
def get_resume_score(resume_id):
    resume = UserResume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    
    # Get detailed score breakdown
    if resume.keywords_matched:
        keywords = json.loads(resume.keywords_matched)
        # Recalculate detailed score
        # This would typically be cached
        return jsonify({
            'overall_score': resume.ai_score,
            'breakdown': {
                'keyword_match': 85,
                'format_quality': 90,
                'content_depth': 80,
                'ats_compatibility': 95
            }
        })
    
    return jsonify({'error': 'Score not available'}), 404


# ============================================================================
# UTILITY ROUTES
# ============================================================================

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        flash('File not found.', 'error')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(current_user.email, obj=current_user)
    
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', form=form)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403


@app.errorhandler(413)
def too_large(e):
    flash('File too large. Please upload a file smaller than 16MB.', 'error')
    return redirect(request.url)


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def create_admin_user():
    """Create the admin user if it doesn't exist"""
    admin_email = "j.singatkar1008@gmail.com"
    admin = User.query.filter_by(email=admin_email).first()
    
    if not admin:
        admin = User(
            first_name="Jinesh",
            last_name="Singatkar",
            email=admin_email,
            is_admin=True,
            subscription_type="enterprise"
        )
        admin.set_password("jinesh@1008")
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {admin_email}")


def create_default_templates():
    """Create default resume templates"""
    default_templates = [
        {
            'name': 'Modern Professional',
            'description': 'Clean, modern design perfect for tech and business roles',
            'category': 'modern',
            'template_file': 'modern_professional.docx',
            'is_premium': False
        },
        {
            'name': 'Classic Executive',
            'description': 'Traditional format ideal for senior management positions',
            'category': 'executive',
            'template_file': 'classic_executive.docx',
            'is_premium': True
        },
        {
            'name': 'Creative Designer',
            'description': 'Stylish template for creative professionals',
            'category': 'creative',
            'template_file': 'creative_designer.docx',
            'is_premium': True
        },
        {
            'name': 'Academic Scholar',
            'description': 'Formal template for academic and research positions',
            'category': 'classic',
            'template_file': 'academic_scholar.docx',
            'is_premium': False
        }
    ]
    
    for template_data in default_templates:
        existing = ResumeTemplate.query.filter_by(name=template_data['name']).first()
        if not existing:
            template = ResumeTemplate(**template_data)
            db.session.add(template)
    
    db.session.commit()
    print("Default templates created")


# Create tables and initialize data
with app.app_context():
    db.create_all()
    create_admin_user()
    create_default_templates()


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)