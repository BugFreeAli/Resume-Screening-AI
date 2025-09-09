from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class Resume(BaseModel):
    """Structured resume data model"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    raw_text: str = Field(..., description="Raw text extracted from resume")
    email: Optional[str] = Field(None, description="Extracted email address")
    phone: Optional[str] = Field(None, description="Extracted phone number")
    skills: List[str] = Field(default_factory=list, description="List of extracted skills")
    skills_by_category: Dict[str, List[str]] = Field(default_factory=dict, description="Skills grouped by category")
    experience: float = Field(0.0, description="Years of experience")  # Changed to float with default
    education: Optional[str] = Field(None, description="Extracted education information")

class JobDescription(BaseModel):
    """Structured job description data model"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    raw_text: str = Field(..., description="Raw text extracted from job description")
    required_skills: List[str] = Field(default_factory=list, description="Required skills for the position")
    preferred_skills: List[str] = Field(default_factory=list, description="Preferred skills for the position")
    skills_by_category: Dict[str, List[str]] = Field(default_factory=dict, description="Skills grouped by category")
    title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    
    @property
    def skills(self) -> List[str]:
        """Get all skills (required + preferred)"""
        return self.required_skills + self.preferred_skills

class MatchResult(BaseModel):
    """Matching result between resume and job description"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    resume: Resume = Field(..., description="Processed resume data")
    job_description: JobDescription = Field(..., description="Processed job description data")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Semantic similarity score (0-1)")
    skill_coverage: float = Field(..., ge=0.0, le=1.0, description="Skill coverage percentage (0-1)")
    skill_density: float = Field(..., ge=0.0, le=1.0, description="Skill density score (0-1)")
    matching_skills: List[str] = Field(default_factory=list, description="Skills that match between resume and JD")
    missing_skills: List[str] = Field(default_factory=list, description="Skills required by JD but missing in resume")
    explanation: str = Field(default="", description="Human-readable explanation of the match results")

# New models for Phase 1
class UserCreate(BaseModel):
    """Model for user registration"""
    email: str = Field(..., description="User email address")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class UserLogin(BaseModel):
    """Model for user login"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Password")

class UserResponse(BaseModel):
    """Model for user response"""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    is_active: bool = Field(..., description="User active status")
    is_admin: bool = Field(..., description="Admin status")
    created_at: datetime = Field(..., description="Account creation date")

class Token(BaseModel):
    """Model for JWT token"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

class TokenData(BaseModel):
    """Model for token data"""
    user_id: Optional[int] = Field(None, description="User ID from token")

class ResumeResponse(BaseModel):
    """Model for resume API response"""
    id: str = Field(..., description="Resume ID")
    data: Resume = Field(..., description="Resume data")

class JDResponse(BaseModel):
    """Model for job description API response"""
    id: str = Field(..., description="Job description ID")
    data: JobDescription = Field(..., description="Job description data")

class BatchProcessRequest(BaseModel):
    """Model for batch processing request"""
    resume_files: List[str] = Field(..., description="List of resume file paths")
    jd_files: List[str] = Field(..., description="List of job description file paths")
    perform_matching: bool = Field(default=False, description="Whether to perform matching after processing")

class BatchProcessResponse(BaseModel):
    """Model for batch processing response"""
    processed_resumes: int = Field(..., description="Number of successfully processed resumes")
    processed_jds: int = Field(..., description="Number of successfully processed job descriptions")
    matches_performed: int = Field(default=0, description="Number of matches performed")
    failed_files: List[str] = Field(default_factory=list, description="List of failed files")
    processing_time: float = Field(..., description="Total processing time in seconds")

class BatchMatchRequest(BaseModel):
    """Model for batch matching request"""
    resume_ids: List[int] = Field(..., description="List of resume IDs to match")
    jd_ids: List[int] = Field(..., description="List of job description IDs to match against")
    weights: Optional[Dict[str, float]] = Field(default=None, description="Optional weights for matching")

class BatchMatchResponse(BaseModel):
    """Model for batch matching response"""
    matches: List[MatchResult] = Field(..., description="List of match results")
    total_matches: int = Field(..., description="Total number of matches performed")
    processing_time: float = Field(..., description="Total processing time in seconds")

class ProcessingStats(BaseModel):
    """Model for processing statistics"""
    total_resumes_processed: int = Field(..., description="Total resumes processed")
    total_jds_processed: int = Field(..., description="Total job descriptions processed")
    total_matches_performed: int = Field(..., description="Total matches performed")
    average_similarity_score: float = Field(..., description="Average similarity score")
    average_skill_coverage: float = Field(..., description="Average skill coverage")
    last_processed_at: Optional[datetime] = Field(None, description="Last processing timestamp")

class ExportRequest(BaseModel):
    """Model for export request"""
    format: str = Field(..., description="Export format (json, csv, pdf)")
    include_raw_text: bool = Field(default=False, description="Include raw text in export")
    include_explanations: bool = Field(default=True, description="Include explanations in export")