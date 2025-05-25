import logging
import re
import os
from openai import OpenAI
import json

class LLMModel:
    def __init__(self):
        """Initialize the LLM model for job description analysis."""
        self.client = None
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)
                logging.info("OpenAI client initialized successfully")
            else:
                logging.warning("No OpenAI API key found, using rule-based analysis")
        except Exception as e:
            logging.warning(f"Could not initialize OpenAI client: {e}")
            self.client = None

    def parse_job_description(self, job_description):
        """
        Parse job description to extract key skills, requirements, and keywords.
        
        Args:
            job_description (str): The job description text
            
        Returns:
            list: List of extracted keywords and requirements
        """
        try:
            if self.client:
                return self._openai_parse_job_description(job_description)
            else:
                return self._rule_based_parse_job_description(job_description)
        except Exception as e:
            logging.error(f"Error parsing job description: {e}")
            return self._basic_keyword_extraction(job_description)

    def _openai_parse_job_description(self, job_description):
        """Use OpenAI to parse job description intelligently."""
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert resume analyst. Extract key skills, technologies, requirements, and qualifications from job descriptions. Return only a JSON array of the most important keywords and requirements, limiting to 15 items."
                    },
                    {
                        "role": "user", 
                        "content": f"Extract key skills and requirements from this job description:\n\n{job_description}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("keywords", [])[:15]
            
        except Exception as e:
            logging.error(f"OpenAI parsing failed: {e}")
            return self._rule_based_parse_job_description(job_description)

    def _rule_based_parse_job_description(self, job_description):
        """Fallback rule-based parsing method."""
        # Clean and preprocess the job description
        cleaned_text = self._clean_text(job_description)
        
        # Extract skills and keywords using multiple approaches
        skills = self._extract_skills(cleaned_text)
        requirements = self._extract_requirements(cleaned_text)
        technologies = self._extract_technologies(cleaned_text)
        
        # Combine all extracted information
        all_keywords = list(set(skills + requirements + technologies))
        
        # Limit to most relevant keywords (top 15)
        return all_keywords[:15]

    def _clean_text(self, text):
        """Clean and normalize text."""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    def _extract_skills(self, text):
        """Extract technical skills from job description."""
        # Common technical skills and tools
        skill_patterns = [
            r'\b(?:Python|Java|JavaScript|C\+\+|C#|Ruby|PHP|Go|Rust|Swift|Kotlin)\b',
            r'\b(?:React|Angular|Vue|Node\.js|Express|Django|Flask|Spring|Laravel)\b',
            r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|Git|GitHub|GitLab)\b',
            r'\b(?:SQL|MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch)\b',
            r'\b(?:Machine Learning|AI|Data Science|Analytics|Big Data)\b',
            r'\b(?:Agile|Scrum|DevOps|CI/CD|TDD|Microservices)\b',
            r'\b(?:HTML|CSS|SASS|LESS|Bootstrap|Tailwind)\b',
            r'\b(?:REST|API|GraphQL|JSON|XML|SOAP)\b'
        ]
        
        skills = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.extend([match.title() for match in matches])
        
        return list(set(skills))

    def _extract_requirements(self, text):
        """Extract requirements and qualifications."""
        requirements = []
        
        # Look for experience requirements
        exp_patterns = [
            r'(\d+)\s*\+?\s*years?\s+(?:of\s+)?experience',
            r'(\d+)\s*\+?\s*years?\s+(?:in|with|of)',
            r'minimum\s+(\d+)\s+years?',
            r'at least\s+(\d+)\s+years?'
        ]
        
        for pattern in exp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                requirements.append(f"{match}+ years experience")
        
        # Look for degree requirements
        degree_patterns = [
            r'bachelor\'?s?\s+degree',
            r'master\'?s?\s+degree',
            r'phd|doctorate',
            r'computer science|engineering|mathematics'
        ]
        
        for pattern in degree_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                match = re.search(pattern, text, re.IGNORECASE).group()
                requirements.append(match.title())
        
        return list(set(requirements))

    def _extract_technologies(self, text):
        """Extract specific technologies and tools."""
        tech_keywords = [
            'cloud', 'database', 'frontend', 'backend', 'fullstack',
            'mobile', 'web development', 'software development',
            'data analysis', 'testing', 'deployment', 'automation',
            'security', 'performance', 'scalability', 'architecture'
        ]
        
        technologies = []
        text_lower = text.lower()
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                technologies.append(keyword.title())
        
        return technologies

    def _basic_keyword_extraction(self, text):
        """Basic fallback keyword extraction."""
        # Simple keyword extraction as fallback
        common_keywords = [
            'Python', 'JavaScript', 'React', 'Node.js', 'AWS', 'Docker',
            'SQL', 'Git', 'Agile', 'API', 'Machine Learning', 'Data Science',
            'Cloud', 'DevOps', 'Testing', 'Frontend', 'Backend'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in common_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords[:10]
