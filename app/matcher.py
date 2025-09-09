import numpy as np
import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple, Optional
from .models import Resume, JobDescription, MatchResult

# Configure logging
logger = logging.getLogger(__name__)

class ResumeMatcher:
    """
    Advanced resume-job description matching system
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the resume matcher
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        try:
            logger.info(f"Initializing ResumeMatcher with model: {model_name}")
            self.model = SentenceTransformer(model_name)
            logger.info("ResumeMatcher initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ResumeMatcher: {e}")
            raise
    
    def _safe_get_experience(self, resume: Resume) -> float:
        """
        Safely get experience value from resume, handling None cases
        
        Args:
            resume: Resume object
            
        Returns:
            Experience as float (0.0 if None or invalid)
        """
        try:
            if hasattr(resume, 'experience'):
                experience = resume.experience
                if experience is None:
                    return 0.0
                # Handle if experience is stored as string
                if isinstance(experience, str):
                    # Extract numbers from string
                    import re
                    numbers = re.findall(r'\d+\.?\d*', experience)
                    return float(numbers[0]) if numbers else 0.0
                return float(experience)
            return 0.0
        except Exception as e:
            logger.error(f"Error getting experience: {e}")
            return 0.0
    
    def _safe_get_skills(self, obj) -> List[str]:
        """
        Safely get skills list, handling None cases
        
        Args:
            obj: Resume or JobDescription object
            
        Returns:
            List of skills (empty list if None)
        """
        try:
            if hasattr(obj, 'skills'):
                skills = obj.skills
                if skills is not None:
                    return skills
                # Handle case where skills might be a property
                if callable(getattr(obj, 'skills', None)):
                    return obj.skills
            return []
        except Exception as e:
            logger.error(f"Error getting skills: {e}")
            return []
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts using sentence transformers
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            if not text1.strip() or not text2.strip():
                return 0.0
                
            embeddings = self.model.encode([text1, text2], normalize_embeddings=True)
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def calculate_skill_coverage(self, resume_skills: List[str], jd_skills: List[str]) -> float:
        """
        Calculate what percentage of JD skills are covered by resume skills
        
        Args:
            resume_skills: Skills from the resume
            jd_skills: Required skills from the job description
            
        Returns:
            Coverage percentage between 0 and 1
        """
        try:
            if not jd_skills:
                return 0.0
            
            # Use safe conversion to sets
            resume_skills_set = set(resume_skills) if resume_skills else set()
            jd_skills_set = set(jd_skills) if jd_skills else set()
            
            matched_skills = resume_skills_set & jd_skills_set
            coverage = len(matched_skills) / len(jd_skills_set) if jd_skills_set else 0.0
            
            logger.debug(f"Skill coverage: {len(matched_skills)}/{len(jd_skills_set)} = {coverage:.2f}")
            return coverage
            
        except Exception as e:
            logger.error(f"Error calculating skill coverage: {e}")
            return 0.0
    
    def calculate_skill_density(self, resume_skills: List[str], jd_skills: List[str]) -> float:
        """
        Calculate skill density (how many of resume skills are relevant to the job)
        
        Args:
            resume_skills: Skills from the resume
            jd_skills: Required skills from the job description
            
        Returns:
            Density score between 0 and 1
        """
        try:
            if not resume_skills:
                return 0.0
            
            # Use safe conversion to sets
            resume_skills_set = set(resume_skills) if resume_skills else set()
            jd_skills_set = set(jd_skills) if jd_skills else set()
            
            relevant_skills = resume_skills_set & jd_skills_set
            density = len(relevant_skills) / len(resume_skills_set) if resume_skills_set else 0.0
            
            return density
            
        except Exception as e:
            logger.error(f"Error calculating skill density: {e}")
            return 0.0
    
    def match_resume_to_jd(self, resume: Resume, jd: JobDescription) -> MatchResult:
        """
        Match a resume to a job description and return comprehensive results
        
        Args:
            resume: Processed resume object
            jd: Processed job description object
            
        Returns:
            MatchResult with comprehensive matching analysis
        """
        try:
            logger.info("Starting resume-JD matching process")
            
            # Safely get skills
            resume_skills = self._safe_get_skills(resume)
            jd_skills = self._safe_get_skills(jd)
            
            # Calculate semantic similarity
            similarity_score = self.calculate_semantic_similarity(
                resume.raw_text if hasattr(resume, 'raw_text') and resume.raw_text else "",
                jd.raw_text if hasattr(jd, 'raw_text') and jd.raw_text else ""
            )
            
            # Calculate skill coverage
            skill_coverage = self.calculate_skill_coverage(resume_skills, jd_skills)
            
            # Calculate skill density
            skill_density = self.calculate_skill_density(resume_skills, jd_skills)
            
            # Identify matching and missing skills
            resume_skills_set = set(resume_skills) if resume_skills else set()
            jd_skills_set = set(jd_skills) if jd_skills else set()
            
            matching_skills = list(resume_skills_set & jd_skills_set)
            missing_skills = list(jd_skills_set - resume_skills_set)
            
            # Generate explanation
            explanation = self._generate_explanation(
                similarity_score, skill_coverage, skill_density,
                matching_skills, missing_skills
            )
            
            logger.info(f"Matching completed. Similarity: {similarity_score:.3f}, Coverage: {skill_coverage:.3f}")
            
            return MatchResult(
                resume=resume,
                job_description=jd,
                similarity_score=similarity_score,
                skill_coverage=skill_coverage,
                skill_density=skill_density,
                matching_skills=matching_skills,
                missing_skills=missing_skills,
                explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"Error in resume-JD matching: {e}")
            raise
    
    def _generate_explanation(self, similarity: float, coverage: float, density: float,
                            matching: List[str], missing: List[str]) -> str:
        """
        Generate human-readable explanation of the match results
        
        Args:
            similarity: Semantic similarity score
            coverage: Skill coverage percentage
            density: Skill density score
            matching: List of matching skills
            missing: List of missing skills
            
        Returns:
            Human-readable explanation
        """
        explanation_parts = []
        
        # Overall match assessment
        overall_score = 0.4 * similarity + 0.4 * coverage + 0.2 * density
        
        if overall_score >= 0.8:
            explanation_parts.append("Excellent overall match for this position.")
        elif overall_score >= 0.6:
            explanation_parts.append("Good match with some areas for improvement.")
        elif overall_score >= 0.4:
            explanation_parts.append("Moderate match - consider additional preparation.")
        else:
            explanation_parts.append("Limited match - significant gaps identified.")
        
        # Semantic similarity interpretation
        if similarity >= 0.7:
            explanation_parts.append("Excellent semantic alignment with the job description.")
        elif similarity >= 0.5:
            explanation_parts.append("Good semantic similarity with the role requirements.")
        else:
            explanation_parts.append("Limited semantic similarity with the job description.")
        
        # Skill coverage interpretation
        if coverage >= 0.8:
            explanation_parts.append("Excellent skill coverage for this role.")
        elif coverage >= 0.6:
            explanation_parts.append("Good skill match for most requirements.")
        elif coverage >= 0.4:
            explanation_parts.append("Moderate skill coverage - some gaps exist.")
        else:
            explanation_parts.append("Significant skill gaps for this position.")
        
        # Specific skills feedback
        if matching:
            explanation_parts.append(f"Strong skills in: {', '.join(matching[:5])}.")
        
        if missing:
            explanation_parts.append(f"Consider developing skills in: {', '.join(missing[:3])}.")
        
        return " ".join(explanation_parts)
    
    def rank_resumes(self, resumes: List[Resume], jd: JobDescription, 
                    weights: Optional[dict] = None) -> List[Tuple[Resume, MatchResult]]:
        """
        Rank multiple resumes against a job description
        
        Args:
            resumes: List of resumes to rank
            jd: Job description to match against
            weights: Optional weights for different scoring components
                    Default: {'skill_coverage': 0.4, 'similarity': 0.4, 'density': 0.2}
        
        Returns:
            List of (resume, match_result) tuples sorted by score
        """
        try:
            if not weights:
                weights = {'skill_coverage': 0.4, 'similarity': 0.4, 'density': 0.2}
            
            results = []
            for resume in resumes:
                match_result = self.match_resume_to_jd(resume, jd)
                
                # Safely get skills for density calculation
                resume_skills = self._safe_get_skills(resume)
                jd_skills = self._safe_get_skills(jd)
                density = self.calculate_skill_density(resume_skills, jd_skills)
                
                # Calculate weighted score
                weighted_score = (
                    weights['skill_coverage'] * match_result.skill_coverage +
                    weights['similarity'] * match_result.similarity_score +
                    weights['density'] * density
                )
                
                results.append((resume, match_result, weighted_score))
            
            # Sort by weighted score (descending)
            results.sort(key=lambda x: x[2], reverse=True)
            
            # Return without the score
            return [(resume, match_result) for resume, match_result, _ in results]
            
        except Exception as e:
            logger.error(f"Error ranking resumes: {e}")
            raise
    
    def get_matching_stats(self) -> dict:
        """
        Get matching system statistics
        
        Returns:
            Dictionary with matching system statistics
        """
        return {
            "model_name": str(self.model),
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
            "max_sequence_length": getattr(self.model, 'max_seq_length', 512)
        }