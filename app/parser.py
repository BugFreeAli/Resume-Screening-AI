import re
import logging
import os
from typing import Tuple, Optional
from pathlib import Path

try:
    from pdfminer.high_level import extract_text
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False
    logging.warning("pdfminer not available. PDF processing will not work.")

try:
    import docx2txt
    DOCX2TXT_AVAILABLE = True
except ImportError:
    DOCX2TXT_AVAILABLE = False
    logging.warning("docx2txt not available. DOCX processing may be limited.")

try:
    from docx import Document
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False
    logging.warning("python-docx not available. DOCX processing will not work.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regex patterns for PII extraction
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}")

# Supported file types
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.rtf'}

def validate_file(file_path: str) -> None:
    """
    Validate file exists and has supported extension
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {file_ext}. Supported types: {', '.join(SUPPORTED_EXTENSIONS)}")

def text_from_file(path: str) -> str:
    """
    Extract text from supported file types (PDF, DOCX, DOC, TXT, RTF)
    
    Args:
        path: Path to the file
        
    Returns:
        Extracted text content
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file type is not supported
        Exception: For other processing errors
    """
    validate_file(path)
    
    file_ext = Path(path).suffix.lower()
    
    try:
        if file_ext == '.pdf':
            if not PDFMINER_AVAILABLE:
                raise ImportError("pdfminer is required for PDF processing")
            return extract_text(path)
            
        elif file_ext == '.docx':
            if DOCX2TXT_AVAILABLE:
                return docx2txt.process(path)
            elif PYTHON_DOCX_AVAILABLE:
                doc = Document(path)
                return "\n".join([p.text for p in doc.paragraphs])
            else:
                raise ImportError("docx2txt or python-docx is required for DOCX processing")
                
        elif file_ext == '.doc':
            # For .doc files, we'd need additional libraries like antiword or textract
            raise ValueError("DOC files are not yet supported. Please convert to DOCX or PDF.")
            
        elif file_ext == '.txt':
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
                
        elif file_ext == '.rtf':
            # Basic RTF text extraction (removes RTF markup)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple RTF markup removal
                content = re.sub(r'\\[a-z0-9-]+\d?', '', content)
                content = re.sub(r'[{}]', '', content)
                return content
                
    except Exception as e:
        logger.error(f"Error processing file {path}: {str(e)}")
        raise Exception(f"Failed to extract text from {path}: {str(e)}")

def extract_pii(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract email and phone number from text
    
    Args:
        text: Text to extract PII from
        
    Returns:
        Tuple of (email, phone) - both can be None if not found
    """
    if not text:
        return None, None
        
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)
    
    return (
        email.group(0) if email else None,
        phone.group(0) if phone else None
    )

def extract_name(text: str) -> Optional[str]:
    """
    Basic name extraction (can be enhanced with NLP libraries)
    
    Args:
        text: Text to extract name from
        
    Returns:
        Extracted name or None
    """
    # This is a basic implementation
    # For production, consider using spaCy or other NLP libraries
    lines = text.split('\n')
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if line and len(line.split()) <= 4:  # Name-like lines
            # Basic heuristics for name detection
            if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', line):
                return line
    return None
