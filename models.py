import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)


class User(UserMixin, db.Model):
    """User accounts with authentication and roles"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    profile_image = db.Column(db.String(255))
    subscription_type = db.Column(db.String(50), default='free')  # 'free', 'premium', 'enterprise'
    resumes_processed = db.Column(db.Integer, default=0)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<User {self.email}>'


class ResumeTemplate(db.Model):
    """Resume templates with different formats and styles"""
    __tablename__ = 'resume_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # 'modern', 'classic', 'creative', 'executive'
    template_file = db.Column(db.String(255), nullable=False)
    preview_image = db.Column(db.String(255))
    is_premium = db.Column(db.Boolean, default=False)
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ResumeTemplate {self.name}>'


class UserResume(db.Model):
    """User's saved resume versions"""
    __tablename__ = 'user_resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    processed_filename = db.Column(db.String(255))
    template_id = db.Column(db.Integer, db.ForeignKey('resume_templates.id'))
    job_description = db.Column(db.Text)
    keywords_matched = db.Column(db.Text)  # JSON string
    ai_score = db.Column(db.Float, default=0.0)  # AI-powered resume score
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('resumes', lazy=True))
    template = db.relationship('ResumeTemplate', backref=db.backref('resumes', lazy=True))
    
    def __repr__(self):
        return f'<UserResume {self.title}>'


class JobApplication(db.Model):
    """Track job applications with resume versions"""
    __tablename__ = 'job_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('user_resumes.id'), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    job_url = db.Column(db.String(500))
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='applied')  # 'applied', 'interview', 'rejected', 'offer'
    notes = db.Column(db.Text)
    
    user = db.relationship('User', backref=db.backref('applications', lazy=True))
    resume = db.relationship('UserResume', backref=db.backref('applications', lazy=True))
    
    def __repr__(self):
        return f'<JobApplication {self.job_title} at {self.company_name}>'


class BatchProcessing(db.Model):
    """Track batch resume processing jobs"""
    __tablename__ = 'batch_processing'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    batch_id = db.Column(db.String(100), unique=True, nullable=False)
    total_files = db.Column(db.Integer, nullable=False)
    processed_files = db.Column(db.Integer, default=0)
    failed_files = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='processing')  # 'processing', 'completed', 'failed'
    job_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    user = db.relationship('User', backref=db.backref('batch_jobs', lazy=True))
    
    def get_progress_percentage(self):
        if self.total_files == 0:
            return 0
        return (self.processed_files / self.total_files) * 100
    
    def __repr__(self):
        return f'<BatchProcessing {self.batch_id}>'

class ResumeSession(db.Model):
    """Track resume modification sessions"""
    __tablename__ = 'resume_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # 'pdf' or 'docx'
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    job_description = db.Column(db.Text, nullable=False)
    keywords_extracted = db.Column(db.Text)  # JSON string of keywords
    processing_time = db.Column(db.Float)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.String(500))
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ResumeSession {self.session_id}>'

class ResumeAnalytics(db.Model):
    """Store analytics and insights"""
    __tablename__ = 'resume_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), db.ForeignKey('resume_sessions.session_id'), nullable=False)
    original_skills_count = db.Column(db.Integer, default=0)
    enhanced_skills_count = db.Column(db.Integer, default=0)
    original_experience_count = db.Column(db.Integer, default=0)
    enhanced_experience_count = db.Column(db.Integer, default=0)
    original_projects_count = db.Column(db.Integer, default=0)
    enhanced_projects_count = db.Column(db.Integer, default=0)
    keyword_match_score = db.Column(db.Float, default=0.0)  # 0-100 score
    improvement_percentage = db.Column(db.Float, default=0.0)
    ai_model_used = db.Column(db.String(50), default='rule-based')  # 'openai' or 'rule-based'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    session = db.relationship('ResumeSession', backref=db.backref('analytics', lazy=True))
    
    def __repr__(self):
        return f'<ResumeAnalytics {self.session_id}>'

class PopularKeywords(db.Model):
    """Track most popular keywords across all resumes"""
    __tablename__ = 'popular_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), unique=True, nullable=False)
    frequency = db.Column(db.Integer, default=1)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50))  # 'skill', 'technology', 'requirement', etc.
    
    def __repr__(self):
        return f'<PopularKeyword {self.keyword}: {self.frequency}>'

class UserFeedback(db.Model):
    """Store user feedback and ratings"""
    __tablename__ = 'user_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), db.ForeignKey('resume_sessions.session_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    feedback_text = db.Column(db.Text)
    helpful = db.Column(db.Boolean)
    suggestions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    session = db.relationship('ResumeSession', backref=db.backref('feedback', lazy=True))
    
    def __repr__(self):
        return f'<UserFeedback {self.session_id}: {self.rating} stars>'