#!/usr/bin/env python3
"""
Database migration script to fix existing data issues
"""

import sqlite3
import json
from pathlib import Path

def migrate_database():
    """Migrate the database to fix data type issues"""
    
    db_path = Path("resume_screening.db")
    if not db_path.exists():
        print("Database not found. Creating new database...")
        return
    
    print("Starting database migration...")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Fix experience field in resumes table
        print("Fixing experience field in resumes table...")
        cursor.execute("""
            UPDATE resumes 
            SET experience = 0.0 
            WHERE experience IS NULL OR experience = ''
        """)
        
        # Fix statistics table
        print("Fixing statistics table...")
        cursor.execute("""
            UPDATE processing_stats 
            SET total_resumes_processed = 0 
            WHERE total_resumes_processed IS NULL
        """)
        
        cursor.execute("""
            UPDATE processing_stats 
            SET total_jds_processed = 0 
            WHERE total_jds_processed IS NULL
        """)
        
        cursor.execute("""
            UPDATE processing_stats 
            SET total_matches_performed = 0 
            WHERE total_matches_performed IS NULL
        """)
        
        cursor.execute("""
            UPDATE processing_stats 
            SET average_similarity_score = 0.0 
            WHERE average_similarity_score IS NULL
        """)
        
        cursor.execute("""
            UPDATE processing_stats 
            SET average_skill_coverage = 0.0 
            WHERE average_skill_coverage IS NULL
        """)
        
        # Commit changes
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
