import pytest
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.pipeline import ProcessingPipeline
from app.matcher import ResumeMatcher

def test_skill_extraction():
    """Test that skills are correctly extracted from text"""
    pipeline = ProcessingPipeline()
    
    test_text = "I have experience with Python, Java, and SQL. Also worked with pandas and numpy."
    skills = pipeline.extract_skills(test_text)
    
    assert "python" in skills
    assert "java" in skills
    assert "sql" in skills
    assert "pandas" in skills
    assert "numpy" in skills

def test_resume_processing():
    """Test resume processing functionality"""
    pipeline = ProcessingPipeline()
    
    # Create a simple test resume file
    test_resume_content = """
    John Doe
    Email: john.doe@email.com
    Phone: 123-456-7890
    
    Skills: Python, Java, SQL, Machine Learning
    
    Experience: Software Engineer at ABC Corp (2020-2023)
    """
    
    test_resume_path = "test_resume.txt"
    with open(test_resume_path, "w") as f:
        f.write(test_resume_content)
    
    try:
        resume = pipeline.process_resume(test_resume_path)
        assert resume.email == "john.doe@email.com"
        assert "python" in resume.skills
        assert "java" in resume.skills
    finally:
        os.remove(test_resume_path)

def test_matching_algorithm():
    """Test the matching algorithm"""
    matcher = ResumeMatcher()
    
    # Test semantic similarity
    text1 = "I am a Python developer with machine learning experience"
    text2 = "We're looking for a Python developer with ML skills"
    similarity = matcher.calculate_semantic_similarity(text1, text2)
    
    assert 0 <= similarity <= 1
    assert similarity > 0.5  # These should be quite similar
    
    # Test skill coverage
    resume_skills = ["python", "sql", "machine learning"]
    jd_skills = ["python", "sql", "docker"]
    coverage = matcher.calculate_skill_coverage(resume_skills, jd_skills)
    
    assert coverage == 2/3  # 2 out of 3 skills matched

if __name__ == "__main__":
    pytest.main([__file__, "-v"])