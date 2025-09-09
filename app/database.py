"""
Database configuration and models for Resume Screening AI
"""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./resume_screening.db")

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resumes = relationship("Resume", back_populates="user")
    job_descriptions = relationship("JobDescription", back_populates="user")
    matches = relationship("Match", back_populates="user")

class Resume(Base):
    """Resume model for storing processed resume data"""
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    email = Column(String)
    phone = Column(String)
    skills = Column(Text)  # JSON string of skills
    skills_by_category = Column(Text)  # JSON string of categorized skills
    experience = Column(Float, default=0.0)
    education = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="resumes")
    matches = relationship("Match", back_populates="resume")

class JobDescription(Base):
    """Job Description model for storing processed JD data"""
    __tablename__ = "job_descriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    required_skills = Column(Text)  # JSON string of required skills
    preferred_skills = Column(Text)  # JSON string of preferred skills
    skills_by_category = Column(Text)  # JSON string of categorized skills
    title = Column(String)
    company = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="job_descriptions")
    matches = relationship("Match", back_populates="job_description")

class Match(Base):
    """Match model for storing matching results"""
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    skill_coverage = Column(Float, nullable=False)
    skill_density = Column(Float, nullable=False)
    matching_skills = Column(Text)  # JSON string of matching skills
    missing_skills = Column(Text)  # JSON string of missing skills
    explanation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="matches")
    resume = relationship("Resume", back_populates="matches")
    job_description = relationship("JobDescription", back_populates="matches")

class ProcessingStats(Base):
    """Model for storing processing statistics"""
    __tablename__ = "processing_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_resumes_processed = Column(Integer, default=0)
    total_jds_processed = Column(Integer, default=0)
    total_matches_performed = Column(Integer, default=0)
    average_similarity_score = Column(Float, default=0.0)
    average_skill_coverage = Column(Float, default=0.0)
    last_processed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database dependency
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
