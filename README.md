# Resume Enhancer

## Overview

Resume Enhancer is a Flask-based web application that allows users to upload, parse, and enhance their resumes. It uses a PostgreSQL database (hosted on Neon) for storing user data, resume templates, and analytics. The application also integrates an LLM (via OpenAI) for resume analysis and scoring.

## Features

- **User Authentication:** Register, log in, and manage your profile.
- **Resume Upload:** Upload your resume (PDF or DOCX) and choose a template.
- **Resume Parsing:** The app parses your resume (using python-docx and PyPDF2) and extracts relevant information.
- **Resume Scoring:** An LLM (or rule-based analysis if no OpenAI API key is provided) scores your resume.
- **Resume Templates:** Choose from a variety of resume templates.
- **Admin Dashboard:** Manage users, templates, and view analytics (if you are an admin).
- **Batch Upload:** (Premium/Enterprise) Upload multiple resumes in one go.

## Prerequisites

- Python (3.9 or higher)
- A PostgreSQL database (for example, hosted on Neon).
- (Optional) An OpenAI API key (for enhanced resume scoring).

## Setup

1. **Clone the repository:**

   ```bash
   git clone <your-repo-url>
   cd ResumeEnhancer
   ```

2. **Create a virtual environment (optional but recommended):**

   ```bash
   python -m venv venv
     (Windows) venv\Scripts\activate
     (Linux/Mac) source venv/bin/activate
   ```

3. **Install dependencies:**

   Run the following command to install all required packages:

   ```bash
   pip install -r requirements.txt
   ```

   (This installs Flask, Flask-SQLAlchemy, Flask-Login, Flask-Bcrypt, Flask-WTF, WTForms, python-dotenv, python-docx, PyPDF2, openai, and psycopg2-binary.)

4. **Environment Variables:**

   Create a file named `.env` in the project root (where `app.py` is located) with the following content (replace the values with your actual PostgreSQL credentials):

   ```
   DATABASE_URL=postgresql://neondb_owner:npg_7psZ3OQdvHwx@ep-rough-butterfly-a6r53n30.us-west-2.aws.neon.tech/neondb?sslmode=require
   PGDATABASE=neondb
   PGHOST=ep-rough-butterfly-a6r53n30.us-west-2.aws.neon.tech
   PGPORT=5432
   PGUSER=neondb_owner
   PGPASSWORD=npg_7psZ3OQdvHwx
   ```

   (If you have an OpenAI API key, you can also add an entry like `OPENAI_API_KEY=your_api_key_here`.)

5. **Run the application:**

   Start the Flask development server with:

   ```bash
   python app.py
   ```

   The app will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Usage

- **Register** a new account (or log in if you already have one).
- **Upload** your resume (PDF or DOCX) and select a template.
- **View** your parsed resume, score, and analytics on the dashboard.
- (Admin) **Manage** users, templates, and view analytics via the admin dashboard.

## Dependencies

- **Flask:** Web framework.
- **Flask-SQLAlchemy:** ORM for database interactions.
- **Flask-Login:** User session management.
- **Flask-Bcrypt:** Password hashing.
- **Flask-WTF & WTForms:** Form handling and validation.
- **python-dotenv:** Loads environment variables from a .env file.
- **python-docx:** Parses DOCX files.
- **PyPDF2:** Parses PDF files.
- **openai:** (Optional) Integrates OpenAI's LLM for resume scoring.
- **psycopg2-binary:** PostgreSQL adapter for Python.

## Notes

- The application is currently running in debug mode (not suitable for production). For production, please configure a WSGI server (e.g., Gunicorn) and set up proper security (e.g., HTTPS).
- If no OpenAI API key is provided, the app falls back to a rule-based resume analysis.

## License

This project is licensed under the MIT License – see the LICENSE file for details. 