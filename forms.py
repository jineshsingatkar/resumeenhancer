from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired, MultipleFileField
from wtforms import StringField, TextAreaField, PasswordField, BooleanField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from models import User


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirm Password', 
                             validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')


class ResumeUploadForm(FlaskForm):
    resume_file = FileField('Resume File', 
                           validators=[FileRequired(), 
                                     FileAllowed(['pdf', 'docx'], 'PDF and DOCX files only!')])
    job_description = TextAreaField('Job Description (Optional)', 
                                   validators=[Length(max=5000)])
    template_id = SelectField('Resume Template', coerce=int, default=1)
    submit = SubmitField('Process Resume')


class BatchUploadForm(FlaskForm):
    resume_files = MultipleFileField('Resume Files', 
                                    validators=[FileRequired(), 
                                              FileAllowed(['pdf', 'docx'], 'PDF and DOCX files only!')])
    job_description = TextAreaField('Job Description', 
                                   validators=[DataRequired(), Length(min=50, max=5000)])
    template_id = SelectField('Resume Template', coerce=int, default=1)
    submit = SubmitField('Process Batch')


class JobApplicationForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=200)])
    job_title = StringField('Job Title', validators=[DataRequired(), Length(max=200)])
    job_url = StringField('Job URL (Optional)', validators=[Length(max=500)])
    status = SelectField('Application Status', 
                        choices=[('applied', 'Applied'), ('interview', 'Interview'), 
                                ('rejected', 'Rejected'), ('offer', 'Job Offer')])
    notes = TextAreaField('Notes', validators=[Length(max=1000)])
    submit = SubmitField('Save Application')


class ProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Update Profile')

    def __init__(self, original_email, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user:
                raise ValidationError('Email already registered. Please use a different email.')


class AdminUserForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    is_admin = BooleanField('Admin Access')
    is_active = BooleanField('Active Account')
    subscription_type = SelectField('Subscription', 
                                   choices=[('free', 'Free'), ('premium', 'Premium'), 
                                          ('enterprise', 'Enterprise')])
    submit = SubmitField('Update User')


class TemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    category = SelectField('Category', 
                          choices=[('modern', 'Modern'), ('classic', 'Classic'), 
                                 ('creative', 'Creative'), ('executive', 'Executive')])
    is_premium = BooleanField('Premium Template')
    template_file = FileField('Template File', 
                             validators=[FileAllowed(['docx'], 'DOCX files only!')])
    preview_image = FileField('Preview Image', 
                             validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Image files only!')])
    submit = SubmitField('Save Template')