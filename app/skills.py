
import yaml
import re
import logging
from typing import List, Dict, Set
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def normalize(text: str) -> str:
    """
    Normalize text for better skill matching.
    - Convert to lowercase
    - Remove extra punctuation and whitespace
    - Handle common variations
    """
    if not text:
        return ""
        
    text = text.lower()
    
    # Handle common variations and abbreviations
    text = re.sub(r'\bml\b', 'machine learning', text)
    text = re.sub(r'\bai\b', 'artificial intelligence', text)
    text = re.sub(r'\bui\b', 'user interface', text)
    text = re.sub(r'\bux\b', 'user experience', text)
    text = re.sub(r'\bapi\b', 'rest apis', text)
    text = re.sub(r'\bdevops\b', 'devops', text)
    
    # Remove extra punctuation and normalize whitespace
    text = re.sub(r"[^a-z0-9+#.\- ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

def load_ontology(path: str = "data/skills_ontology.yml") -> Dict[str, List[str]]:
    """
    Load skills ontology from YAML file with error handling
    
    Args:
        path: Path to the ontology file
        
    Returns:
        Dictionary mapping categories to skill lists
        
    Raises:
        FileNotFoundError: If ontology file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    try:
        ontology_path = Path(path)
        if not ontology_path.exists():
            raise FileNotFoundError(f"Ontology file not found: {path}")
            
        with open(ontology_path, "r", encoding="utf-8") as f:
            ontology = yaml.safe_load(f)
            
        if not isinstance(ontology, dict):
            raise ValueError("Ontology must be a dictionary")
            
        # Validate structure
        for category, skills in ontology.items():
            if not isinstance(skills, list):
                raise ValueError(f"Category '{category}' must contain a list of skills")
            if not all(isinstance(skill, str) for skill in skills):
                raise ValueError(f"All skills in category '{category}' must be strings")
                
        logger.info(f"Loaded ontology with {len(ontology)} categories")
        return ontology
        
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading ontology from {path}: {e}")
        raise

def extract_skills(text: str, ontology: Dict[str, List[str]]) -> List[str]:
    """
    Extract skills from text using the ontology
    
    Args:
        text: Text to extract skills from
        ontology: Skills ontology dictionary
        
    Returns:
        List of extracted skills (normalized)
    """
    if not text or not ontology:
        return []
        
    norm_text = normalize(text)
    found = set()
    
    for category, skills in ontology.items():
        for skill in skills:
            # Exact match with word boundaries
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, norm_text):
                found.add(skill)
                
            # Also check for hyphenated versions
            if "-" in skill:
                hyphen_pattern = r"\b" + re.escape(skill.lower().replace("-", " ")) + r"\b"
                if re.search(hyphen_pattern, norm_text):
                    found.add(skill)
    
    return sorted(found)

def extract_skills_with_categories(text: str, ontology: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Extract skills and group them by category
    
    Args:
        text: Text to extract skills from
        ontology: Skills ontology dictionary
        
    Returns:
        Dictionary mapping categories to found skills
    """
    if not text or not ontology:
        return {}
        
    norm_text = normalize(text)
    skills_by_category = {}
    
    for category, skills in ontology.items():
        category_skills = []
        for skill in skills:
            # Exact match with word boundaries
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, norm_text):
                category_skills.append(skill)
                
            # Also check for hyphenated versions
            if "-" in skill:
                hyphen_pattern = r"\b" + re.escape(skill.lower().replace("-", " ")) + r"\b"
                if re.search(hyphen_pattern, norm_text):
                    category_skills.append(skill)
        
        if category_skills:
            skills_by_category[category] = sorted(list(set(category_skills)))
    
    return skills_by_category

def get_skill_suggestions(text: str, ontology: Dict[str, List[str]], max_suggestions: int = 5) -> List[str]:
    """
    Get skill suggestions based on text content
    
    Args:
        text: Text to analyze
        ontology: Skills ontology dictionary
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        List of suggested skills
    """
    if not text or not ontology:
        return []
        
    norm_text = normalize(text)
    suggestions = []
    
    # Look for partial matches
    for category, skills in ontology.items():
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower in norm_text and skill not in suggestions:
                suggestions.append(skill)
                if len(suggestions) >= max_suggestions:
                    break
        if len(suggestions) >= max_suggestions:
            break
    
    return suggestions[:max_suggestions]

def calculate_skill_overlap(skills1: List[str], skills2: List[str]) -> float:
    """
    Calculate the overlap between two skill lists
    
    Args:
        skills1: First list of skills
        skills2: Second list of skills
        
    Returns:
        Overlap percentage (0.0 to 1.0)
    """
    if not skills1 or not skills2:
        return 0.0
        
    set1 = set(skills1)
    set2 = set(skills2)
    
    intersection = set1 & set2
    union = set1 | set2
    
    return len(intersection) / len(union) if union else 0.0