#!/usr/bin/env python3
"""
Resume Screening AI - Main Entry Point
"""

import argparse
from app.pipeline import ProcessingPipeline
from app.matcher import ResumeMatcher

def main():
    parser = argparse.ArgumentParser(description="Resume Screening AI")
    parser.add_argument("--resume", help="Path to resume file")
    parser.add_argument("--jd", help="Path to job description file")
    parser.add_argument("--api", action="store_true", help="Start FastAPI server")
    parser.add_argument("--ui", action="store_true", help="Start Streamlit UI")
    
    args = parser.parse_args()
    
    if args.api:
        # Start FastAPI server
        import uvicorn
        uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)
    
    elif args.ui:
        # Start Streamlit UI
        import subprocess
        subprocess.run(["streamlit", "run", "ui/app.py"])
    
    elif args.resume and args.jd:
        # Process single resume and JD
        pipeline = ProcessingPipeline()
        matcher = ResumeMatcher()
        
        print("Processing resume...")
        resume = pipeline.process_resume(args.resume)
        
        print("Processing job description...")
        jd = pipeline.process_job_description(args.jd)
        
        print("Matching...")
        result = matcher.match_resume_to_jd(resume, jd)
        
        print(f"\nMatch Results:")
        print(f"Similarity Score: {result.similarity_score:.3f}")
        print(f"Skill Coverage: {result.skill_coverage:.1%}")
        print(f"Matching Skills: {', '.join(result.matching_skills)}")
        if result.missing_skills:
            print(f"Missing Skills: {', '.join(result.missing_skills)}")
        print(f"\nExplanation: {result.explanation}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()