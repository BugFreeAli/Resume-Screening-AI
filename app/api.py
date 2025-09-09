import json
import time
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Optional
import os
import uuid
from sqlalchemy.orm import Session
from .pipeline import ProcessingPipeline
from .matcher import ResumeMatcher
from .models import (
    Resume, JobDescription, MatchResult, UserCreate, UserLogin, UserResponse,
    Token, ResumeResponse, JDResponse, BatchProcessRequest, BatchProcessResponse,
    BatchMatchRequest, BatchMatchResponse, ProcessingStats, ExportRequest
)
from .database import get_db, create_tables, User, Resume as DBResume, JobDescription as DBJobDescription, Match as DBMatch, ProcessingStats as DBProcessingStats
from .auth import auth_handler, authenticate_user, create_user, get_current_active_user, get_current_admin_user
from pydantic import BaseModel

app = FastAPI(title="Resume Screening API", version="2.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
pipeline = ProcessingPipeline()
matcher = ResumeMatcher()

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()

# Authentication endpoints
@app.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        user = create_user(
            db=db,
            email=user_data.email,
            username=user_data.username,
            password=user_data.password
        )
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token"""
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_handler.create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at
    )

# Resume endpoints
@app.post("/upload/resume/", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and process a resume"""
    try:
        # Create unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = f"data/uploads/{unique_filename}"
        
        # Ensure upload directory exists
        os.makedirs("data/uploads", exist_ok=True)
        
        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process resume
        resume_data = pipeline.process_resume(file_path)
        
        # Save to database
        db_resume = DBResume(
            user_id=current_user.id,
            filename=file.filename,
            file_path=file_path,
            raw_text=resume_data.raw_text,
            email=resume_data.email,
            phone=resume_data.phone,
            skills=json.dumps(resume_data.skills),
            skills_by_category=json.dumps(resume_data.skills_by_category),
            experience=float(resume_data.experience),
            education=resume_data.education
        )
        
        db.add(db_resume)
        try:
            db.commit()
            db.refresh(db_resume)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        # Update processing stats
        stats = db.query(DBProcessingStats).filter(DBProcessingStats.user_id == current_user.id).first()
        if not stats:
            stats = DBProcessingStats(user_id=current_user.id)
            db.add(stats)
        
        # Handle None values in statistics
        if stats.total_resumes_processed is None:
            stats.total_resumes_processed = 0
        stats.total_resumes_processed += 1
        stats.last_processed_at = datetime.utcnow()
        db.commit()
        
        return ResumeResponse(id=str(db_resume.id), data=resume_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")

@app.post("/upload/jd/", response_model=JDResponse)
async def upload_job_description(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and process a job description"""
    try:
        # Create unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = f"data/uploads/{unique_filename}"
        
        # Ensure upload directory exists
        os.makedirs("data/uploads", exist_ok=True)
        
        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process JD
        jd_data = pipeline.process_job_description(file_path)
        
        # Save to database
        db_jd = DBJobDescription(
            user_id=current_user.id,
            filename=file.filename,
            file_path=file_path,
            raw_text=jd_data.raw_text,
            required_skills=json.dumps(jd_data.required_skills),
            preferred_skills=json.dumps(jd_data.preferred_skills),
            skills_by_category=json.dumps(jd_data.skills_by_category),
            title=jd_data.title,
            company=jd_data.company
        )
        
        db.add(db_jd)
        db.commit()
        db.refresh(db_jd)
        
        # Update processing stats
        stats = db.query(DBProcessingStats).filter(DBProcessingStats.user_id == current_user.id).first()
        if not stats:
            stats = DBProcessingStats(user_id=current_user.id)
            db.add(stats)
        
        # Handle None values in statistics
        if stats.total_jds_processed is None:
            stats.total_jds_processed = 0
        stats.total_jds_processed += 1
        stats.last_processed_at = datetime.utcnow()
        db.commit()
        
        return JDResponse(id=str(db_jd.id), data=jd_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing job description: {str(e)}")

@app.post("/match/", response_model=MatchResult)
async def match_resume_to_jd(
    resume_id: str,
    jd_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Match a specific resume to a job description"""
    try:
        # Get resume and JD from database
        db_resume = db.query(DBResume).filter(
            DBResume.id == int(resume_id),
            DBResume.user_id == current_user.id
        ).first()
        
        db_jd = db.query(DBJobDescription).filter(
            DBJobDescription.id == int(jd_id),
            DBJobDescription.user_id == current_user.id
        ).first()
        
        if not db_resume:  # ← This line and the next were not indented properly
            raise HTTPException(status_code=404, detail="Resume not found")
        if not db_jd:  # ← This line and the next were not indented properly
            raise HTTPException(status_code=404, detail="Job description not found")
        
        # Convert database objects to Pydantic models
        resume = Resume(
            raw_text=db_resume.raw_text,
            email=db_resume.email,
            phone=db_resume.phone,
            skills=json.loads(db_resume.skills),
            skills_by_category=json.loads(db_resume.skills_by_category),
            experience=float(db_resume.experience) if db_resume.experience is not None else 0.0,
            education=db_resume.education
        )
        
        jd = JobDescription(
            raw_text=db_jd.raw_text,
            required_skills=json.loads(db_jd.required_skills),
            preferred_skills=json.loads(db_jd.preferred_skills),
            skills_by_category=json.loads(db_jd.skills_by_category),
            title=db_jd.title,
            company=db_jd.company
        )
        
        # Perform matching
        result = matcher.match_resume_to_jd(resume, jd)  # ← This line was also not indented properly
        
        # Save match result to database
        db_match = DBMatch(
            user_id=current_user.id,
            resume_id=db_resume.id,
            job_description_id=db_jd.id,
            similarity_score=result.similarity_score,
            skill_coverage=result.skill_coverage,
            skill_density=result.skill_density,
            matching_skills=json.dumps(result.matching_skills),
            missing_skills=json.dumps(result.missing_skills),
            explanation=result.explanation
        )
        
        db.add(db_match)
        
        # Update processing stats
        stats = db.query(DBProcessingStats).filter(DBProcessingStats.user_id == current_user.id).first()
        if not stats:
            stats = DBProcessingStats(user_id=current_user.id)
            db.add(stats)
        
        stats.total_matches_performed += 1
        # Handle None values in stats
        current_avg_sim = stats.average_similarity_score or 0.0
        current_avg_cov = stats.average_skill_coverage or 0.0
        stats.average_similarity_score = (current_avg_sim + result.similarity_score) / 2
        stats.average_skill_coverage = (current_avg_cov + result.skill_coverage) / 2
        db.commit()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching: {str(e)}")

@app.get("/resumes/", response_model=List[Resume])
async def list_resumes(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all resumes for the current user"""
    db_resumes = db.query(DBResume).filter(DBResume.user_id == current_user.id).all()
    
    resumes = []
    for db_resume in db_resumes:
        resume = Resume(
            raw_text=db_resume.raw_text,
            email=db_resume.email,
            phone=db_resume.phone,
            skills=json.loads(db_resume.skills),
            skills_by_category=json.loads(db_resume.skills_by_category),
            experience=float(db_resume.experience) if db_resume.experience is not None else 0.0,
            education=db_resume.education
        )
        resumes.append(resume)
    
    return resumes

@app.get("/jds/", response_model=List[JobDescription])
async def list_job_descriptions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all job descriptions for the current user"""
    db_jds = db.query(DBJobDescription).filter(DBJobDescription.user_id == current_user.id).all()
    
    jds = []
    for db_jd in db_jds:
        jd = JobDescription(
            raw_text=db_jd.raw_text,
            required_skills=json.loads(db_jd.required_skills),
            preferred_skills=json.loads(db_jd.preferred_skills),
            skills_by_category=json.loads(db_jd.skills_by_category),
            title=db_jd.title,
            company=db_jd.company
        )
        jds.append(jd)
    
    return jds

@app.get("/stats/", response_model=ProcessingStats)
async def get_processing_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get processing statistics for the current user"""
    stats = db.query(DBProcessingStats).filter(DBProcessingStats.user_id == current_user.id).first()
    
    if not stats:
        return ProcessingStats(
            total_resumes_processed=0,
            total_jds_processed=0,
            total_matches_performed=0,
            average_similarity_score=0.0,
            average_skill_coverage=0.0
        )
    
    return ProcessingStats(
        total_resumes_processed=stats.total_resumes_processed,
        total_jds_processed=stats.total_jds_processed,
        total_matches_performed=stats.total_matches_performed,
        average_similarity_score=stats.average_similarity_score,
        average_skill_coverage=stats.average_skill_coverage,
        last_processed_at=stats.last_processed_at
    )

@app.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Process multiple resumes and job descriptions in batch"""
    start_time = time.time()
    processed_resumes = 0
    processed_jds = 0
    failed_files = []
    
    try:
        # Process resumes
        for resume_file in request.resume_files:
            try:
                resume_data = pipeline.process_resume(resume_file)
                
                # Save to database
                db_resume = DBResume(
                    user_id=current_user.id,
                    filename=os.path.basename(resume_file),
                    file_path=resume_file,
                    raw_text=resume_data.raw_text,
                    email=resume_data.email,
                    phone=resume_data.phone,
                    skills=json.dumps(resume_data.skills),
                    skills_by_category=json.dumps(resume_data.skills_by_category),
                    experience=float(resume_data.experience),
                    education=resume_data.education
                )
                
                db.add(db_resume)
                processed_resumes += 1
                
            except Exception as e:
                failed_files.append(f"Resume: {resume_file} - {str(e)}")
        
        # Process job descriptions
        for jd_file in request.jd_files:
            try:
                jd_data = pipeline.process_job_description(jd_file)
                
                # Save to database
                db_jd = DBJobDescription(
                    user_id=current_user.id,
                    filename=os.path.basename(jd_file),
                    file_path=jd_file,
                    raw_text=jd_data.raw_text,
                    required_skills=json.dumps(jd_data.required_skills),
                    preferred_skills=json.dumps(jd_data.preferred_skills),
                    skills_by_category=json.dumps(jd_data.skills_by_category),
                    title=jd_data.title,
                    company=jd_data.company
                )
                
                db.add(db_jd)
                processed_jds += 1
                
            except Exception as e:
                failed_files.append(f"JD: {jd_file} - {str(e)}")
        
        db.commit()
        
        # Perform matching if requested
        matches_performed = 0
        if request.perform_matching and processed_resumes > 0 and processed_jds > 0:
            try:
                # Get the newly processed resumes and JDs
                new_resumes = db.query(DBResume).filter(
                    DBResume.user_id == current_user.id
                ).order_by(DBResume.id.desc()).limit(processed_resumes).all()
                
                new_jds = db.query(DBJobDescription).filter(
                    DBJobDescription.user_id == current_user.id
                ).order_by(DBJobDescription.id.desc()).limit(processed_jds).all()
                
                # Perform matching for each resume against each JD
                for resume in new_resumes:
                    for jd in new_jds:
                        try:
                            # Convert database objects to Pydantic models
                            resume_data = Resume(
                                raw_text=resume.raw_text,
                                email=resume.email,
                                phone=resume.phone,
                                skills=json.loads(resume.skills),
                                skills_by_category=json.loads(resume.skills_by_category),
                                experience=float(resume.experience) if resume.experience is not None else 0.0,
                                education=resume.education
                            )
                            
                            jd_data = JobDescription(
                                raw_text=jd.raw_text,
                                required_skills=json.loads(jd.required_skills),
                                preferred_skills=json.loads(jd.preferred_skills),
                                skills_by_category=json.loads(jd.skills_by_category),
                                title=jd.title,
                                company=jd.company
                            )
                            
                            # Perform matching
                            match_result = matcher.match_resume_to_jd(resume_data, jd_data)
                            
                            # Save match to database
                            db_match = DBMatch(
                                user_id=current_user.id,
                                resume_id=resume.id,
                                job_description_id=jd.id,
                                similarity_score=match_result.similarity_score,
                                skill_coverage=match_result.skill_coverage,
                                skill_density=match_result.skill_density,
                                matching_skills=json.dumps(match_result.matching_skills),
                                missing_skills=json.dumps(match_result.missing_skills),
                                explanation=match_result.explanation
                            )
                            
                            db.add(db_match)
                            matches_performed += 1
                            
                        except Exception as e:
                            logger.error(f"Error matching resume {resume.id} to JD {jd.id}: {e}")
                            failed_files.append(f"Match: Resume {resume.id} to JD {jd.id} - {str(e)}")
                
                db.commit()
                
            except Exception as e:
                logger.error(f"Error in batch matching: {e}")
                failed_files.append(f"Batch matching failed: {str(e)}")
        
        # Update stats
        stats = db.query(DBProcessingStats).filter(DBProcessingStats.user_id == current_user.id).first()
        if not stats:
            stats = DBProcessingStats(user_id=current_user.id)
            db.add(stats)
        
        # Handle None values in statistics
        if stats.total_resumes_processed is None:
            stats.total_resumes_processed = 0
        if stats.total_jds_processed is None:
            stats.total_jds_processed = 0
        if stats.total_matches_performed is None:
            stats.total_matches_performed = 0
        stats.total_resumes_processed += processed_resumes
        stats.total_jds_processed += processed_jds
        stats.total_matches_performed += matches_performed
        stats.last_processed_at = datetime.utcnow()
        db.commit()
        
        processing_time = time.time() - start_time
        
        return BatchProcessResponse(
            processed_resumes=processed_resumes,
            processed_jds=processed_jds,
            matches_performed=matches_performed,
            failed_files=failed_files,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@app.post("/batch/match", response_model=BatchMatchResponse)
async def batch_match(
    request: BatchMatchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Perform batch matching between existing resumes and job descriptions"""
    start_time = time.time()
    matches = []
    
    try:
        # Get resumes and JDs from database
        resumes = db.query(DBResume).filter(
            DBResume.id.in_(request.resume_ids),
            DBResume.user_id == current_user.id
        ).all()
        
        jds = db.query(DBJobDescription).filter(
            DBJobDescription.id.in_(request.jd_ids),
            DBJobDescription.user_id == current_user.id
        ).all()
        
        if not resumes:
            raise HTTPException(status_code=400, detail="No valid resumes found")
        if not jds:
            raise HTTPException(status_code=400, detail="No valid job descriptions found")
        
        # Perform matching for each resume against each JD
        for resume in resumes:
            for jd in jds:
                try:
                    # Convert database objects to Pydantic models
                    resume_data = Resume(
                        raw_text=resume.raw_text,
                        email=resume.email,
                        phone=resume.phone,
                        skills=json.loads(resume.skills),
                        skills_by_category=json.loads(resume.skills_by_category),
                        experience=float(resume.experience) if resume.experience is not None else 0.0,
                        education=resume.education
                    )
                    
                    jd_data = JobDescription(
                        raw_text=jd.raw_text,
                        required_skills=json.loads(jd.required_skills),
                        preferred_skills=json.loads(jd.preferred_skills),
                        skills_by_category=json.loads(jd.skills_by_category),
                        title=jd.title,
                        company=jd.company
                    )
                    
                    # Perform matching
                    match_result = matcher.match_resume_to_jd(resume_data, jd_data)
                    
                    # Save match to database
                    db_match = DBMatch(
                        user_id=current_user.id,
                        resume_id=resume.id,
                        job_description_id=jd.id,
                        similarity_score=match_result.similarity_score,
                        skill_coverage=match_result.skill_coverage,
                        skill_density=match_result.skill_density,
                        matching_skills=json.dumps(match_result.matching_skills),
                        missing_skills=json.dumps(match_result.missing_skills),
                        explanation=match_result.explanation
                    )
                    
                    db.add(db_match)
                    matches.append(match_result)
                    
                except Exception as e:
                    logger.error(f"Error matching resume {resume.id} to JD {jd.id}: {e}")
        
        db.commit()
        
        # Update stats
        stats = db.query(DBProcessingStats).filter(DBProcessingStats.user_id == current_user.id).first()
        if not stats:
            stats = DBProcessingStats(user_id=current_user.id)
            db.add(stats)
        
        if stats.total_matches_performed is None:
            stats.total_matches_performed = 0
        stats.total_matches_performed += len(matches)
        stats.last_processed_at = datetime.utcnow()
        db.commit()
        
        processing_time = time.time() - start_time
        
        return BatchMatchResponse(
            matches=matches,
            total_matches=len(matches),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in batch matching: {e}")
        raise HTTPException(status_code=500, detail=f"Batch matching failed: {str(e)}")

@app.get("/resumes/")
async def get_user_resumes(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all resumes for the current user"""
    try:
        db_resumes = db.query(DBResume).filter(DBResume.user_id == current_user.id).all()
        resumes = []
        for db_resume in db_resumes:
            resume = Resume(
                raw_text=db_resume.raw_text,
                email=db_resume.email,
                phone=db_resume.phone,
                skills=json.loads(db_resume.skills),
                skills_by_category=json.loads(db_resume.skills_by_category),
                experience=float(db_resume.experience) if db_resume.experience is not None else 0.0,
                education=db_resume.education
            )
            resumes.append(ResumeResponse(id=str(db_resume.id), data=resume))
        return resumes
    except Exception as e:
        logger.error(f"Error getting resumes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get resumes: {str(e)}")

@app.get("/jds/")
async def get_user_jds(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all job descriptions for the current user"""
    try:
        db_jds = db.query(DBJobDescription).filter(DBJobDescription.user_id == current_user.id).all()
        jds = []
        for db_jd in db_jds:
            jd = JobDescription(
                raw_text=db_jd.raw_text,
                required_skills=json.loads(db_jd.required_skills),
                preferred_skills=json.loads(db_jd.preferred_skills),
                skills_by_category=json.loads(db_jd.skills_by_category),
                title=db_jd.title,
                company=db_jd.company
            )
            jds.append(JDResponse(id=str(db_jd.id), data=jd))
        return jds
    except Exception as e:
        logger.error(f"Error getting job descriptions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job descriptions: {str(e)}")

@app.get("/matches/")
async def get_user_matches(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all matches for the current user"""
    try:
        db_matches = db.query(DBMatch).filter(DBMatch.user_id == current_user.id).all()
        matches = []
        for db_match in db_matches:
            # Get resume and JD data
            resume = db.query(DBResume).filter(DBResume.id == db_match.resume_id).first()
            jd = db.query(DBJobDescription).filter(DBJobDescription.id == db_match.job_description_id).first()
            
            if resume and jd:
                resume_data = Resume(
                    raw_text=resume.raw_text,
                    email=resume.email,
                    phone=resume.phone,
                    skills=json.loads(resume.skills),
                    skills_by_category=json.loads(resume.skills_by_category),
                    experience=float(resume.experience) if resume.experience is not None else 0.0,
                    education=resume.education
                )
                
                jd_data = JobDescription(
                    raw_text=jd.raw_text,
                    required_skills=json.loads(jd.required_skills),
                    preferred_skills=json.loads(jd.preferred_skills),
                    skills_by_category=json.loads(jd.skills_by_category),
                    title=jd.title,
                    company=jd.company
                )
                
                match_result = MatchResult(
                    resume=resume_data,
                    job_description=jd_data,
                    similarity_score=db_match.similarity_score,
                    skill_coverage=db_match.skill_coverage,
                    skill_density=db_match.skill_density,
                    matching_skills=json.loads(db_match.matching_skills),
                    missing_skills=json.loads(db_match.missing_skills),
                    explanation=db_match.explanation
                )
                matches.append(match_result)
        return matches
    except Exception as e:
        logger.error(f"Error getting matches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get matches: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)