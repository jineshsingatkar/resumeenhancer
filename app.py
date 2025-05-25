import os
import logging
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import uuid
from resume_modifier.llm_model import LLMModel
from resume_modifier.resume_parser import ResumeParser
from resume_modifier.resume_formatter import ResumeFormatter
from docx import Document
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
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
            else:
                flash('Invalid file name.', 'error')
                return render_template('index.html')

            # Initialize LLM Model
            llm = LLMModel()

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

            # Clean up uploaded file
            try:
                os.remove(upload_path)
            except Exception as e:
                logging.warning(f"Could not remove uploaded file: {e}")

            logging.debug(f"Resume modification completed. Output saved to: {output_path}")
            flash('Resume modified successfully!', 'success')
            
            return render_template('result.html', 
                                 output_filename=output_filename,
                                 original_data=resume_data,
                                 modified_data=modified_resume_data,
                                 job_requirements=parsed_job_description)

        except Exception as e:
            logging.error(f"Error processing resume: {str(e)}")
            flash(f'Error processing resume: {str(e)}', 'error')
            
            # Clean up files on error
            try:
                if 'upload_path' in locals():
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
