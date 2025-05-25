import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

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