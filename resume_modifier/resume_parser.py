import logging
from docx import Document
import re
import PyPDF2
import os

class ResumeParser:
    def __init__(self, resume_path):
        """
        Initialize the resume parser with a DOCX file path.
        
        Args:
            resume_path (str): Path to the resume DOCX file
        """
        self.resume_path = resume_path

    def parse_resume(self):
        """
        Parse the resume document and extract structured data.
        
        Returns:
            dict: Structured resume data with summary, skills, experience, and projects
        """
        try:
            # Check if file is PDF or DOCX
            if self.resume_path.lower().endswith('.pdf'):
                return self._parse_pdf_resume()
            else:
                return self._parse_docx_resume()
                
        except Exception as e:
            logging.error(f"Error parsing resume: {e}")
            return {
                "summary": "Professional with diverse experience",
                "skills": ["Communication", "Teamwork", "Problem Solving"],
                "experience": [],
                "projects": [],
                "education": [],
                "contact_info": {},
                "raw_text": ""
            }
    
    def _parse_pdf_resume(self):
        """Parse PDF resume file."""
        try:
            with open(self.resume_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                all_text = []
                
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        all_text.extend(text.split('\n'))
                
                return self._process_text_data(all_text)
                
        except Exception as e:
            logging.error(f"Error parsing PDF: {e}")
            return self._get_default_resume_data()
    
    def _parse_docx_resume(self):
        """Parse DOCX resume file."""
        try:
            doc = Document(self.resume_path)
            all_text = []
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    all_text.append(text)
            
            return self._process_text_data(all_text)
                
        except Exception as e:
            logging.error(f"Error parsing DOCX: {e}")
            return self._get_default_resume_data()
    
    def _process_text_data(self, all_text):
        """Process extracted text data from either PDF or DOCX."""
        resume_data = {
            "summary": "",
            "skills": [],
            "experience": [],
            "projects": [],
            "education": [],
            "contact_info": {},
            "raw_text": ""
        }
        
        current_section = None
        
        for text in all_text:
            if not text.strip():
                continue
                
            # Identify sections
            section = self._identify_section(text)
            if section:
                current_section = section
                continue
            
            # Parse content based on current section
            if current_section == "summary":
                resume_data["summary"] = self._parse_summary(text, resume_data["summary"])
            elif current_section == "skills":
                resume_data["skills"].extend(self._parse_skills(text))
            elif current_section == "experience":
                resume_data["experience"].extend(self._parse_experience(text))
            elif current_section == "projects":
                resume_data["projects"].extend(self._parse_projects(text))
            elif current_section == "education":
                resume_data["education"].extend(self._parse_education(text))
            elif current_section == "contact":
                resume_data["contact_info"].update(self._parse_contact(text))
        
        # Join all text for backup processing
        resume_data["raw_text"] = "\n".join(all_text)
        
        # If sections weren't clearly identified, try alternative parsing
        if not resume_data["summary"] and not resume_data["skills"]:
            resume_data = self._fallback_parsing(all_text, resume_data)
        
        # Clean up and deduplicate
        resume_data = self._clean_resume_data(resume_data)
        
        logging.debug(f"Parsed resume data: {resume_data}")
        return resume_data
    
    def _get_default_resume_data(self):
        """Return default resume data structure."""
        return {
            "summary": "Professional with diverse experience",
            "skills": ["Communication", "Teamwork", "Problem Solving"],
            "experience": [],
            "projects": [],
            "education": [],
            "contact_info": {},
            "raw_text": ""
        }

    def _identify_section(self, text):
        """Identify which section a paragraph belongs to."""
        text_lower = text.lower()
        
        # Section headers
        if any(keyword in text_lower for keyword in ['summary', 'profile', 'objective', 'about']):
            return "summary"
        elif any(keyword in text_lower for keyword in ['skills', 'technical skills', 'competencies']):
            return "skills"
        elif any(keyword in text_lower for keyword in ['experience', 'work experience', 'employment', 'professional experience']):
            return "experience"
        elif any(keyword in text_lower for keyword in ['projects', 'project experience', 'notable projects']):
            return "projects"
        elif any(keyword in text_lower for keyword in ['education', 'academic', 'qualification']):
            return "education"
        elif any(keyword in text_lower for keyword in ['contact', 'personal information', 'details']):
            return "contact"
        
        return None

    def _parse_summary(self, text, existing_summary):
        """Parse summary/profile text."""
        # Skip section headers
        if self._identify_section(text):
            return existing_summary
        
        if existing_summary:
            return f"{existing_summary} {text}"
        return text

    def _parse_skills(self, text):
        """Parse skills from text."""
        skills = []
        
        # Split by common delimiters
        delimiters = [',', '|', '•', '·', ';', '\n']
        text_parts = [text]
        
        for delimiter in delimiters:
            new_parts = []
            for part in text_parts:
                new_parts.extend(part.split(delimiter))
            text_parts = new_parts
        
        for part in text_parts:
            skill = part.strip()
            if skill and len(skill) > 1 and not self._identify_section(skill):
                skills.append(skill)
        
        return skills

    def _parse_experience(self, text):
        """Parse work experience entries."""
        experience = []
        
        # Look for company names, positions, dates
        if any(keyword in text.lower() for keyword in ['company', 'corporation', 'inc', 'ltd', 'llc']):
            experience.append(text)
        elif re.search(r'\d{4}', text):  # Contains year
            experience.append(text)
        elif any(keyword in text.lower() for keyword in ['engineer', 'developer', 'manager', 'analyst', 'specialist']):
            experience.append(text)
        
        return experience

    def _parse_projects(self, text):
        """Parse project entries."""
        projects = []
        
        # Look for project indicators
        if any(keyword in text.lower() for keyword in ['project', 'developed', 'built', 'created', 'implemented']):
            projects.append(text)
        elif text.startswith('-') or text.startswith('•'):
            projects.append(text.lstrip('-•').strip())
        
        return projects

    def _parse_education(self, text):
        """Parse education entries."""
        education = []
        
        if any(keyword in text.lower() for keyword in ['university', 'college', 'degree', 'bachelor', 'master', 'phd']):
            education.append(text)
        
        return education

    def _parse_contact(self, text):
        """Parse contact information."""
        contact = {}
        
        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            contact['email'] = email_match.group()
        
        # Phone
        phone_match = re.search(r'[\+]?[1-9]?[0-9]{7,14}', text)
        if phone_match:
            contact['phone'] = phone_match.group()
        
        return contact

    def _fallback_parsing(self, all_text, resume_data):
        """Fallback parsing when sections aren't clearly identified."""
        combined_text = " ".join(all_text)
        
        # Extract skills using common patterns
        skill_indicators = ['proficient in', 'experienced with', 'skilled in', 'expertise in']
        for indicator in skill_indicators:
            if indicator in combined_text.lower():
                # Extract text following the indicator
                start = combined_text.lower().find(indicator)
                if start != -1:
                    following_text = combined_text[start:start+200]
                    skills = self._parse_skills(following_text)
                    resume_data["skills"].extend(skills)
        
        # Use first few sentences as summary if none found
        if not resume_data["summary"]:
            sentences = combined_text.split('.')[:3]
            resume_data["summary"] = '. '.join(sentences).strip()
        
        return resume_data

    def _clean_resume_data(self, resume_data):
        """Clean and deduplicate resume data."""
        # Remove duplicates from lists
        resume_data["skills"] = list(set(resume_data["skills"]))
        resume_data["experience"] = list(set(resume_data["experience"]))
        resume_data["projects"] = list(set(resume_data["projects"]))
        resume_data["education"] = list(set(resume_data["education"]))
        
        # Filter out very short or invalid entries
        resume_data["skills"] = [skill for skill in resume_data["skills"] if len(skill) > 2]
        
        return resume_data
