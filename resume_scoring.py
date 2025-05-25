import json
import re
from collections import Counter
from resume_modifier.llm_model import LLMModel


class ResumeScorer:
    """AI-powered resume scoring system"""
    
    def __init__(self):
        self.llm_model = LLMModel()
        
    def calculate_comprehensive_score(self, resume_data, job_description, keywords_matched):
        """Calculate comprehensive AI-powered resume score"""
        try:
            # Individual scoring components
            keyword_score = self._calculate_keyword_score(resume_data, keywords_matched)
            format_score = self._calculate_format_score(resume_data)
            content_score = self._calculate_content_score(resume_data)
            relevance_score = self._calculate_relevance_score(resume_data, job_description)
            ats_score = self._calculate_ats_compatibility(resume_data)
            
            # Weighted final score
            final_score = (
                keyword_score * 0.25 +      # 25% - Keyword matching
                content_score * 0.25 +      # 25% - Content quality
                relevance_score * 0.20 +    # 20% - Job relevance
                format_score * 0.15 +       # 15% - Format structure
                ats_score * 0.15            # 15% - ATS compatibility
            )
            
            return {
                'overall_score': round(final_score, 1),
                'keyword_score': round(keyword_score, 1),
                'format_score': round(format_score, 1),
                'content_score': round(content_score, 1),
                'relevance_score': round(relevance_score, 1),
                'ats_score': round(ats_score, 1),
                'recommendations': self._generate_recommendations(
                    keyword_score, format_score, content_score, relevance_score, ats_score
                ),
                'strengths': self._identify_strengths(resume_data),
                'improvements': self._suggest_improvements(resume_data, job_description)
            }
            
        except Exception as e:
            return {
                'overall_score': 0.0,
                'error': f"Scoring failed: {str(e)}",
                'recommendations': ["Please try uploading your resume again."]
            }
    
    def _calculate_keyword_score(self, resume_data, keywords_matched):
        """Calculate score based on keyword matching"""
        if not keywords_matched:
            return 0.0
            
        try:
            keywords = json.loads(keywords_matched) if isinstance(keywords_matched, str) else keywords_matched
            if not keywords:
                return 0.0
                
            resume_text = self._extract_resume_text(resume_data).lower()
            matched_count = 0
            
            for keyword in keywords:
                if keyword.lower() in resume_text:
                    matched_count += 1
            
            match_percentage = (matched_count / len(keywords)) * 100
            
            # Score out of 100
            if match_percentage >= 80:
                return 95.0
            elif match_percentage >= 60:
                return 85.0
            elif match_percentage >= 40:
                return 70.0
            elif match_percentage >= 20:
                return 55.0
            else:
                return 30.0
                
        except Exception:
            return 0.0
    
    def _calculate_format_score(self, resume_data):
        """Calculate score based on resume format and structure"""
        score = 0.0
        
        # Check for essential sections
        if resume_data.get('summary'):
            score += 20
        if resume_data.get('skills') and len(resume_data['skills']) > 0:
            score += 25
        if resume_data.get('experience') and len(resume_data['experience']) > 0:
            score += 25
        if resume_data.get('education') and len(resume_data['education']) > 0:
            score += 15
        if resume_data.get('contact'):
            score += 15
            
        return min(score, 100.0)
    
    def _calculate_content_score(self, resume_data):
        """Calculate score based on content quality"""
        score = 0.0
        
        # Summary quality
        summary = resume_data.get('summary', '')
        if summary:
            if len(summary) >= 100:
                score += 20
            elif len(summary) >= 50:
                score += 15
            else:
                score += 5
        
        # Skills count and variety
        skills = resume_data.get('skills', [])
        if len(skills) >= 10:
            score += 25
        elif len(skills) >= 5:
            score += 20
        elif len(skills) >= 3:
            score += 15
        
        # Experience depth
        experience = resume_data.get('experience', [])
        if experience:
            avg_description_length = sum(len(exp.get('description', '')) for exp in experience) / len(experience)
            if avg_description_length >= 200:
                score += 30
            elif avg_description_length >= 100:
                score += 25
            elif avg_description_length >= 50:
                score += 15
        
        # Projects (bonus points)
        projects = resume_data.get('projects', [])
        if projects:
            score += min(len(projects) * 5, 25)
        
        return min(score, 100.0)
    
    def _calculate_relevance_score(self, resume_data, job_description):
        """Calculate relevance to job description using AI"""
        if not job_description:
            return 75.0  # Default score when no job description
            
        try:
            # Use AI to analyze relevance
            resume_text = self._extract_resume_text(resume_data)
            
            # Simple relevance calculation based on common terms
            job_words = set(re.findall(r'\b\w+\b', job_description.lower()))
            resume_words = set(re.findall(r'\b\w+\b', resume_text.lower()))
            
            common_words = job_words.intersection(resume_words)
            relevance_ratio = len(common_words) / len(job_words) if job_words else 0
            
            return min(relevance_ratio * 100, 100.0)
            
        except Exception:
            return 50.0
    
    def _calculate_ats_compatibility(self, resume_data):
        """Calculate ATS (Applicant Tracking System) compatibility score"""
        score = 100.0
        
        # Check for common ATS issues
        resume_text = self._extract_resume_text(resume_data)
        
        # Penalize for special characters in excess
        special_char_count = len(re.findall(r'[^\w\s]', resume_text))
        if special_char_count > 50:
            score -= 10
        
        # Check for consistent formatting
        if not resume_data.get('contact'):
            score -= 15
        
        # Reward for standard section names
        standard_sections = ['summary', 'skills', 'experience', 'education']
        for section in standard_sections:
            if resume_data.get(section):
                score += 5
        
        return max(score, 0.0)
    
    def _extract_resume_text(self, resume_data):
        """Extract all text from resume data"""
        text_parts = []
        
        if resume_data.get('summary'):
            text_parts.append(resume_data['summary'])
        
        if resume_data.get('skills'):
            text_parts.extend(resume_data['skills'])
        
        if resume_data.get('experience'):
            for exp in resume_data['experience']:
                text_parts.append(exp.get('description', ''))
        
        if resume_data.get('projects'):
            for project in resume_data['projects']:
                text_parts.append(project.get('description', ''))
        
        return ' '.join(text_parts)
    
    def _generate_recommendations(self, keyword_score, format_score, content_score, relevance_score, ats_score):
        """Generate improvement recommendations based on scores"""
        recommendations = []
        
        if keyword_score < 70:
            recommendations.append("Include more relevant keywords from the job description")
        
        if format_score < 80:
            recommendations.append("Improve resume structure by adding missing sections")
        
        if content_score < 70:
            recommendations.append("Expand descriptions and add more detailed accomplishments")
        
        if relevance_score < 70:
            recommendations.append("Better align your experience with the job requirements")
        
        if ats_score < 80:
            recommendations.append("Optimize for ATS compatibility by using standard formatting")
        
        if not recommendations:
            recommendations.append("Great job! Your resume is well-optimized for this position")
        
        return recommendations
    
    def _identify_strengths(self, resume_data):
        """Identify resume strengths"""
        strengths = []
        
        if resume_data.get('summary') and len(resume_data['summary']) > 100:
            strengths.append("Strong professional summary")
        
        if len(resume_data.get('skills', [])) >= 8:
            strengths.append("Comprehensive skills section")
        
        if len(resume_data.get('experience', [])) >= 3:
            strengths.append("Solid work experience")
        
        if resume_data.get('projects'):
            strengths.append("Relevant project experience")
        
        return strengths or ["Resume shows potential for improvement"]
    
    def _suggest_improvements(self, resume_data, job_description):
        """Suggest specific improvements"""
        improvements = []
        
        if not resume_data.get('summary'):
            improvements.append("Add a professional summary at the top")
        
        if len(resume_data.get('skills', [])) < 5:
            improvements.append("Include more relevant technical and soft skills")
        
        if not resume_data.get('projects'):
            improvements.append("Add relevant projects to showcase your abilities")
        
        experience = resume_data.get('experience', [])
        if experience:
            short_descriptions = [exp for exp in experience if len(exp.get('description', '')) < 100]
            if short_descriptions:
                improvements.append("Expand experience descriptions with specific achievements")
        
        return improvements or ["Consider tailoring content more specifically to this role"]