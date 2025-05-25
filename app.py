import os
import logging
import time
import json
from datetime import datetime
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import uuid
from resume_modifier.llm_model import LLMModel
from resume_modifier.resume_parser import ResumeParser
from resume_modifier.resume_formatter import ResumeFormatter
from docx import Document
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
else:
    # Fallback for development
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///resume_modifier.db"

db.init_app(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'docx', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload and output directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Import models after db initialization
from models import ResumeSession, ResumeAnalytics, PopularKeywords, UserFeedback

# Create database tables
with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session_id = str(uuid.uuid4())
        start_time = time.time()
        upload_path = None
        
        try:
            # Check if job description was provided
            job_description = request.form.get('job_description', '').strip()
            if not job_description:
                flash('Please provide a job description.', 'error')
                return render_template('index.html')

            # Check if file was uploaded
            if 'resume_file' not in request.files:
                flash('No file uploaded.', 'error')
                return render_template('index.html')

            file = request.files['resume_file']
            if file.filename == '':
                flash('No file selected.', 'error')
                return render_template('index.html')

            if not file or not allowed_file(file.filename):
                flash('Please upload a valid DOCX or PDF file.', 'error')
                return render_template('index.html')

            # Save uploaded file
            if file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(upload_path)
                
                # Get file info
                file_size = os.path.getsize(upload_path)
                file_type = filename.rsplit('.', 1)[1].lower()
            else:
                flash('Invalid file name.', 'error')
                return render_template('index.html')

            # Initialize LLM Model
            llm = LLMModel()
            ai_model_used = 'openai' if llm.client else 'rule-based'

            # Parse Job Description
            logging.debug(f"Parsing job description: {job_description[:100]}...")
            parsed_job_description = llm.parse_job_description(job_description)

            # Parse Resume
            logging.debug(f"Parsing resume from: {upload_path}")
            parser = ResumeParser(upload_path)
            resume_data = parser.parse_resume()

            # Modify Resume
            logging.debug("Modifying resume based on job requirements")
            formatter = ResumeFormatter()
            modified_resume_data = formatter.modify_resume(resume_data, parsed_job_description)

            # Create modified resume document
            doc = Document()
            formatter.add_content(doc, modified_resume_data)
            
            # Save modified resume
            output_filename = f"modified_resume_{uuid.uuid4().hex}.docx"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            doc.save(output_path)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Save session to database
            session_record = ResumeSession(
                session_id=session_id,
                original_filename=filename,
                file_type=file_type,
                file_size=file_size,
                job_description=job_description,
                keywords_extracted=json.dumps(parsed_job_description),
                processing_time=processing_time,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:500],
                success=True
            )
            db.session.add(session_record)

            # Calculate analytics
            original_skills_count = len(resume_data.get('skills', []))
            enhanced_skills_count = len(modified_resume_data.get('skills', []))
            original_experience_count = len(resume_data.get('experience', []))
            enhanced_experience_count = len(modified_resume_data.get('experience', []))
            original_projects_count = len(resume_data.get('projects', []))
            enhanced_projects_count = len(modified_resume_data.get('projects', []))
            
            # Calculate improvement percentage
            total_original = original_skills_count + original_experience_count + original_projects_count
            total_enhanced = enhanced_skills_count + enhanced_experience_count + enhanced_projects_count
            improvement_percentage = ((total_enhanced - total_original) / max(total_original, 1)) * 100 if total_original > 0 else 0

            # Save analytics
            analytics = ResumeAnalytics(
                session_id=session_id,
                original_skills_count=original_skills_count,
                enhanced_skills_count=enhanced_skills_count,
                original_experience_count=original_experience_count,
                enhanced_experience_count=enhanced_experience_count,
                original_projects_count=original_projects_count,
                enhanced_projects_count=enhanced_projects_count,
                improvement_percentage=improvement_percentage,
                ai_model_used=ai_model_used
            )
            db.session.add(analytics)

            # Update popular keywords
            for keyword in parsed_job_description:
                existing_keyword = PopularKeywords.query.filter_by(keyword=keyword).first()
                if existing_keyword:
                    existing_keyword.frequency += 1
                    existing_keyword.last_seen = datetime.now()
                else:
                    new_keyword = PopularKeywords(keyword=keyword, category='extracted')
                    db.session.add(new_keyword)

            db.session.commit()

            # Clean up uploaded file
            try:
                if upload_path:
                    os.remove(upload_path)
            except Exception as e:
                logging.warning(f"Could not remove uploaded file: {e}")

            logging.debug(f"Resume modification completed. Output saved to: {output_path}")
            flash('Resume modified successfully!', 'success')
            
            return render_template('result.html', 
                                 output_filename=output_filename,
                                 original_data=resume_data,
                                 modified_data=modified_resume_data,
                                 job_requirements=parsed_job_description,
                                 session_id=session_id,
                                 analytics=analytics)

        except Exception as e:
            logging.error(f"Error processing resume: {str(e)}")
            
            # Save failed session
            try:
                processing_time = time.time() - start_time
                failed_session = ResumeSession(
                    session_id=session_id,
                    original_filename=file.filename if 'file' in locals() else 'unknown',
                    file_type='unknown',
                    file_size=0,
                    job_description=job_description if 'job_description' in locals() else '',
                    processing_time=processing_time,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')[:500],
                    success=False,
                    error_message=str(e)
                )
                db.session.add(failed_session)
                db.session.commit()
            except:
                pass
            
            flash(f'Error processing resume: {str(e)}', 'error')
            
            # Clean up files on error
            try:
                if upload_path and os.path.exists(upload_path):
                    os.remove(upload_path)
            except:
                pass
                
            return render_template('index.html')

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Ensure filename is secure
        secure_name = secure_filename(filename)
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], secure_name)
        
        if not os.path.exists(file_path):
            flash('File not found.', 'error')
            return redirect(url_for('index'))
            
        return send_file(file_path, as_attachment=True, download_name=f"modified_resume.docx")
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        flash('Error downloading file.', 'error')
        return redirect(url_for('index'))

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Please upload a file smaller than 16MB.', 'error')
    return render_template('index.html'), 413

@app.errorhandler(500)
def internal_error(e):
    logging.error(f"Internal server error: {str(e)}")
    flash('An internal error occurred. Please try again.', 'error')
    return render_template('index.html'), 500

@app.route('/analytics')
def analytics_dashboard():
    """Display analytics dashboard with database insights"""
    try:
        # Get total sessions
        total_sessions = ResumeSession.query.count()
        successful_sessions = ResumeSession.query.filter_by(success=True).count()
        
        # Get recent sessions
        recent_sessions = ResumeSession.query.order_by(ResumeSession.created_at.desc()).limit(10).all()
        
        # Get popular keywords
        popular_keywords = PopularKeywords.query.order_by(PopularKeywords.frequency.desc()).limit(20).all()
        
        # Get file type statistics
        pdf_count = ResumeSession.query.filter_by(file_type='pdf').count()
        docx_count = ResumeSession.query.filter_by(file_type='docx').count()
        
        # Calculate success rate
        success_rate = (successful_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        # Get average processing time
        avg_processing_time = db.session.query(db.func.avg(ResumeSession.processing_time)).filter_by(success=True).scalar() or 0
        
        # Get analytics data
        analytics_data = ResumeAnalytics.query.join(ResumeSession).filter(ResumeSession.success == True).all()
        
        return render_template('analytics.html',
                             total_sessions=total_sessions,
                             successful_sessions=successful_sessions,
                             success_rate=round(success_rate, 1),
                             avg_processing_time=round(avg_processing_time, 2),
                             recent_sessions=recent_sessions,
                             popular_keywords=popular_keywords,
                             pdf_count=pdf_count,
                             docx_count=docx_count,
                             analytics_data=analytics_data)
                             
    except Exception as e:
        logging.error(f"Error loading analytics: {e}")
        flash('Unable to load analytics data.', 'error')
        return redirect(url_for('index'))

@app.route('/feedback/<session_id>', methods=['POST'])
def submit_feedback(session_id):
    """Submit user feedback for a session"""
    try:
        rating = request.form.get('rating', type=int)
        feedback_text = request.form.get('feedback_text', '').strip()
        helpful = request.form.get('helpful') == 'yes'
        
        if not rating or rating < 1 or rating > 5:
            flash('Please provide a valid rating (1-5 stars).', 'error')
            return redirect(url_for('index'))
        
        feedback = UserFeedback(
            session_id=session_id,
            rating=rating,
            feedback_text=feedback_text,
            helpful=helpful
        )
        db.session.add(feedback)
        db.session.commit()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        logging.error(f"Error submitting feedback: {e}")
        flash('Unable to submit feedback.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
