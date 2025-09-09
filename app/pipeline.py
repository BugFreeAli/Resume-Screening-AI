import logging
from typing import List, Optional, Dict
from pathlib import Path
from .parser import text_from_file, extract_pii, extract_name
from .skills import load_ontology, extract_skills, extract_skills_with_categories, get_skill_suggestions
from .models import Resume, JobDescription

# Configure logging
logger = logging.getLogger(__name__)

class ProcessingPipeline:
    """
    Main pipeline for processing resumes and job descriptions
    """
    
    def __init__(self, ontology_path: str = "data/skills_ontology.yml"):
        """
        Initialize the processing pipeline
        
        Args:
            ontology_path: Path to the skills ontology file
        """
        try:
            self.ontology = load_ontology(ontology_path)
            logger.info("ProcessingPipeline initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ProcessingPipeline: {e}")
            raise
    
    def extract_skills(self, text: str) -> List[str]:
        """
        Extract normalized skills from raw text using the loaded ontology
        
        Args:
            text: Raw text to extract skills from
            
        Returns:
            List of extracted skills
        """
        try:
            return extract_skills(text, self.ontology)
        except Exception as e:
            logger.error(f"Error extracting skills: {e}")
            return []
    
    def _extract_experience(self, text: str) -> float:
        """
        Extract years of experience from resume text
        
        Args:
            text: Resume text
            
        Returns:
            Years of experience (0.0 if not found)
        """
        try:
            import re
            
            # Common patterns for experience
            patterns = [
                r'(\d+)\s*\+?\s*years?[\s\w]*experience',
                r'experience.*?(\d+)\s*\+?\s*years?',
                r'(\d+)\s*\+?\s*years?.*?experience',
                r'(\d+)\s*yr',
                r'(\d+)\s*yr\.',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Take the highest number found (most likely total experience)
                    years = max([float(match) for match in matches if match.isdigit()])
                    return years
            
            # If no explicit experience found, try to infer from dates
            # Look for date ranges that might indicate work experience
            date_pattern = r'(\d{4}[\s\-–]*\d{4}|\d{4}[\s\-–]*(?:present|current|now))'
            date_matches = re.findall(date_pattern, text, re.IGNORECASE)
            
            if date_matches:
                # Simple heuristic: count date ranges as potential experience
                return min(float(len(date_matches)), 15.0)  # Cap at 15 years
            
            return 0.0  # Default to 0 if no experience found
            
        except Exception as e:
            logger.error(f"Error extracting experience: {e}")
            return 0.0
    
    def process_resume(self, file_path: str) -> Resume:
        """
        Process a resume file and extract structured information
        
        Args:
            file_path: Path to the resume file
            
        Returns:
            Processed Resume object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type is not supported
            Exception: For other processing errors
        """
        try:
            logger.info(f"Processing resume: {file_path}")
            
            # Extract text
            raw_text = text_from_file(file_path)
            if not raw_text.strip():
                raise ValueError("No text content found in the file")
            
            # Extract PII
            email, phone = extract_pii(raw_text)
            
            # Extract name (basic implementation)
            name = extract_name(raw_text)
            
            # Extract skills
            skills = extract_skills(raw_text, self.ontology)
            skills_by_category = extract_skills_with_categories(raw_text, self.ontology)
            
            # Extract experience - ADDED
            experience = self._extract_experience(raw_text)
            
            # Get skill suggestions
            suggestions = get_skill_suggestions(raw_text, self.ontology)
            
            logger.info(f"Resume processed successfully. Found {len(skills)} skills, {experience} years experience")
            
            return Resume(
                raw_text=raw_text,
                email=email,
                phone=phone,
                skills=skills,
                skills_by_category=skills_by_category,
                experience=experience,
                education=name  # Use name as education for now
            )
            
        except Exception as e:
            logger.error(f"Error processing resume {file_path}: {e}")
            raise
    
    def process_job_description(self, file_path: str, 
                              required_skills: Optional[List[str]] = None) -> JobDescription:
        """
        Process a job description file
        
        Args:
            file_path: Path to the job description file
            required_skills: Optional list of explicitly required skills
            
        Returns:
            Processed JobDescription object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type is not supported
            Exception: For other processing errors
        """
        try:
            logger.info(f"Processing job description: {file_path}")
            
            # Extract text
            raw_text = text_from_file(file_path)
            if not raw_text.strip():
                raise ValueError("No text content found in the file")
            
            # Extract skills (treat all as required unless specified)
            extracted_skills = extract_skills(raw_text, self.ontology)
            
            # Use provided required skills or extract from text
            final_required_skills = required_skills if required_skills else extracted_skills
            skills_by_category = extract_skills_with_categories(raw_text, self.ontology)
            
            # Extract job title and company (basic implementation)
            title = self._extract_job_title(raw_text)
            company = self._extract_company(raw_text)
            
            logger.info(f"Job description processed successfully. Found {len(final_required_skills)} required skills")
            
            return JobDescription(
                raw_text=raw_text,
                required_skills=final_required_skills,
                skills_by_category=skills_by_category,
                title=title,
                company=company
            )
            
        except Exception as e:
            logger.error(f"Error processing job description {file_path}: {e}")
            raise
    
    def process_multiple_resumes(self, file_paths: List[str]) -> List[Resume]:
        """
        Process multiple resume files
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            List of processed Resume objects
        """
        resumes = []
        failed_files = []
        
        for file_path in file_paths:
            try:
                resume = self.process_resume(file_path)
                resumes.append(resume)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                failed_files.append(file_path)
        
        if failed_files:
            logger.warning(f"Failed to process {len(failed_files)} files: {failed_files}")
        
        logger.info(f"Successfully processed {len(resumes)} out of {len(file_paths)} resumes")
        return resumes
    
    def _extract_job_title(self, text: str) -> Optional[str]:
        """
        Basic job title extraction
        """
        # This is a basic implementation
        # For production, consider using NLP libraries
        lines = text.split('\n')
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if line and len(line.split()) <= 6:  # Title-like lines
                # Look for common title indicators
                if any(keyword in line.lower() for keyword in ['engineer', 'developer', 'analyst', 'manager', 'specialist']):
                    return line
        return None
    
    def _extract_company(self, text: str) -> Optional[str]:
        """
        Basic company name extraction
        """
        # This is a basic implementation
        # For production, consider using NLP libraries
        lines = text.split('\n')
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if line and len(line.split()) <= 4:  # Company-like lines
                # Look for common company indicators
                if any(keyword in line.lower() for keyword in ['inc', 'corp', 'llc', 'ltd', 'company']):
                    return line
        return None
    
    def get_processing_stats(self) -> dict:
        """
        Get processing pipeline statistics
        
        Returns:
            Dictionary with pipeline statistics
        """
        return {
            "ontology_categories": len(self.ontology),
            "total_skills": sum(len(skills) for skills in self.ontology.values()),
            "supported_file_types": [".pdf", ".docx", ".txt", ".rtf"]
        }