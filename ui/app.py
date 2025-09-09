import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List
import requests
import os
import json
from datetime import datetime
import time

# API configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="Resume Screening AI v2.0",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #c3e6cb;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "token" not in st.session_state:
        st.session_state.token = None
    if "user" not in st.session_state:
        st.session_state.user = None
    if "resumes" not in st.session_state:
        st.session_state.resumes = []
    if "jds" not in st.session_state:
        st.session_state.jds = []
    if "matches" not in st.session_state:
        st.session_state.matches = []
    if "stats" not in st.session_state:
        st.session_state.stats = None

def load_user_data():
    """Load user's resumes, job descriptions, and matches"""
    if "token" in st.session_state:
        try:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            
            # Load resumes
            resp = requests.get(f"{API_BASE_URL}/resumes/", headers=headers)
            if resp.status_code == 200:
                st.session_state.resumes = resp.json()
            
            # Load job descriptions
            resp = requests.get(f"{API_BASE_URL}/jds/", headers=headers)
            if resp.status_code == 200:
                st.session_state.jds = resp.json()
            
            # Load matches
            resp = requests.get(f"{API_BASE_URL}/matches/", headers=headers)
            if resp.status_code == 200:
                st.session_state.matches = resp.json()
                
        except Exception as e:
            st.error(f"Failed to load user data: {str(e)}")

def login_page():
    """Login/Register page"""
    st.markdown('<h1 class="main-header">Resume Screening AI v2.0</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.header("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                try:
                    response = requests.post(f"{API_BASE_URL}/auth/login", json={
                        "email": email,
                        "password": password
                    })
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.authenticated = True
                        
                        # Get user info
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        user_response = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)
                        if user_response.status_code == 200:
                            st.session_state.user = user_response.json()
                        
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
    
    with tab2:
        st.header("Register")
        with st.form("register_form"):
            email = st.text_input("Email", key="reg_email")
            username = st.text_input("Username", key="reg_username")
            password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Register")
            
            if submit:
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    try:
                        response = requests.post(f"{API_BASE_URL}/auth/register", json={
                            "email": email,
                            "username": username,
                            "password": password
                        })
                        
                        if response.status_code == 200:
                            st.success("Registration successful! Please login.")
                        else:
                            st.error(f"Registration failed: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Registration failed: {str(e)}")

def main_dashboard():
    """Main dashboard after authentication"""
    # Header with user info
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown('<h1 class="main-header">Resume Screening AI v2.0</h1>', unsafe_allow_html=True)
    with col2:
        st.metric("User", st.session_state.user["username"])
    with col3:
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "📄 Upload", "🔍 Matching", "📈 Analytics", "⚙️ Settings"])
    
    with tab1:
        dashboard_tab()
    
    with tab2:
        upload_tab()
    
    with tab3:
        matching_tab()
    
    with tab4:
        analytics_tab()
    
    with tab5:
        settings_tab()

def dashboard_tab():
    """Dashboard tab with overview and statistics"""
    st.header("📊 Dashboard Overview")
    
    # Get processing stats
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        stats_response = requests.get(f"{API_BASE_URL}/stats/", headers=headers)
        if stats_response.status_code == 200:
            st.session_state.stats = stats_response.json()
    except:
        pass
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Resumes Processed",
            st.session_state.stats.get("total_resumes_processed", 0) if st.session_state.stats else 0,
            help="Total number of resumes processed"
        )
    
    with col2:
        st.metric(
            "Job Descriptions",
            st.session_state.stats.get("total_jds_processed", 0) if st.session_state.stats else 0,
            help="Total number of job descriptions processed"
        )
    
    with col3:
        st.metric(
            "Matches Performed",
            st.session_state.stats.get("total_matches_performed", 0) if st.session_state.stats else 0,
            help="Total number of matches performed"
        )
    
    with col4:
        avg_score = st.session_state.stats.get("average_similarity_score", 0) if st.session_state.stats else 0
        st.metric(
            "Avg Similarity",
            f"{avg_score:.2f}",
            help="Average similarity score across all matches"
        )
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.stats:
            # Processing activity chart
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="gauge+number+delta",
                value=st.session_state.stats.get("average_skill_coverage", 0) * 100,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Average Skill Coverage (%)"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Recent activity
        st.subheader("Recent Activity")
        if st.session_state.stats and st.session_state.stats.get("last_processed_at"):
            try:
                # Handle both timestamp and datetime objects
                last_processed = st.session_state.stats["last_processed_at"]
                if isinstance(last_processed, (int, float)):
                    last_processed = datetime.fromtimestamp(last_processed)
                elif isinstance(last_processed, str):
                    last_processed = datetime.fromisoformat(last_processed.replace('Z', '+00:00'))
                st.info(f"Last processed: {last_processed.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                st.info("No recent activity")
        else:
            st.info("No recent activity")

def upload_tab():
    """Upload tab with enhanced file processing"""
    st.header("📄 Upload Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upload Resume")
        resume_file = st.file_uploader(
            "Choose resume file",
            type=["pdf", "docx", "txt"],
            key="resume_uploader"
        )
        
        if resume_file and st.button("Process Resume", key="process_resume"):
            with st.spinner("Processing resume..."):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    files = {"file": (resume_file.name, resume_file.getvalue(), resume_file.type)}
                    response = requests.post(f"{API_BASE_URL}/upload/resume/", files=files, headers=headers)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.resumes.append(result)
                        st.success("✅ Resume processed successfully!")
                        
                        # Show extracted information
                        data = result["data"]
                        with st.expander("View extracted information"):
                            st.write(f"**Email:** {data.get('email', 'N/A')}")
                            st.write(f"**Phone:** {data.get('phone', 'N/A')}")
                            st.write(f"**Skills Found:** {', '.join(data.get('skills', []))}")
                    else:
                        st.error(f"❌ Error processing resume: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")
    
    with col2:
        st.subheader("Upload Job Description")
        jd_file = st.file_uploader(
            "Choose job description file",
            type=["pdf", "docx", "txt"],
            key="jd_uploader"
        )
        
        if jd_file and st.button("Process JD", key="process_jd"):
            with st.spinner("Processing job description..."):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    files = {"file": (jd_file.name, jd_file.getvalue(), jd_file.type)}
                    response = requests.post(f"{API_BASE_URL}/upload/jd/", files=files, headers=headers)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.jds.append(result)
                        st.success("✅ Job description processed successfully!")
                        
                        # Show extracted information
                        data = result["data"]
                        with st.expander("View extracted information"):
                            st.write(f"**Title:** {data.get('title', 'N/A')}")
                            st.write(f"**Company:** {data.get('company', 'N/A')}")
                            st.write(f"**Required Skills:** {', '.join(data.get('required_skills', []))}")
                    else:
                        st.error(f"❌ Error processing job description: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")
    
    # Batch processing
    st.subheader("🔄 Batch Processing")
    st.info("Upload multiple files at once for efficient processing")
    
    batch_resumes = st.file_uploader(
        "Upload multiple resumes",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="batch_resumes"
    )
    
    batch_jds = st.file_uploader(
        "Upload multiple job descriptions",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="batch_jds"
    )
    
    # Add checkbox for batch matching
    perform_matching = st.checkbox("Perform matching after processing", value=True, help="Automatically match all resumes against all job descriptions")
    
    if (batch_resumes or batch_jds) and st.button("Process Batch"):
        with st.spinner("Processing batch files..."):
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                
                # First, upload all files individually to get their IDs
                resume_ids = []
                jd_ids = []
                
                # Upload resumes
                for file in batch_resumes:
                    try:
                        files = {"file": (file.name, file.getvalue(), file.type)}
                        response = requests.post(f"{API_BASE_URL}/upload/resume/", files=files, headers=headers)
                        if response.status_code == 200:
                            resume_result = response.json()
                            resume_ids.append(resume_result["id"])
                    except Exception as e:
                        st.error(f"Failed to upload {file.name}: {str(e)}")
                
                # Upload job descriptions
                for file in batch_jds:
                    try:
                        files = {"file": (file.name, file.getvalue(), file.type)}
                        response = requests.post(f"{API_BASE_URL}/upload/jd/", files=files, headers=headers)
                        if response.status_code == 200:
                            jd_result = response.json()
                            jd_ids.append(jd_result["id"])
                    except Exception as e:
                        st.error(f"Failed to upload {file.name}: {str(e)}")
                
                processed_count = len(resume_ids) + len(jd_ids)
                
                # Perform batch matching if requested and we have both resumes and JDs
                if perform_matching and resume_ids and jd_ids:
                    st.info("Performing batch matching...")
                    
                    batch_match_data = {
                        "resume_ids": resume_ids,
                        "jd_ids": jd_ids,
                        "weights": {
                            "skill_coverage": 0.4,
                            "similarity": 0.4,
                            "density": 0.2
                        }
                    }
                    
                    match_response = requests.post(
                        f"{API_BASE_URL}/batch/match",
                        json=batch_match_data,
                        headers=headers
                    )
                    
                    if match_response.status_code == 200:
                        batch_result = match_response.json()
                        matches_performed = batch_result['total_matches']
                        st.success(f"✅ Successfully processed {processed_count} files and performed {matches_performed} matches!")
                        
                        # Display batch match results
                        if batch_result['matches']:
                            st.subheader("📊 Batch Match Results")
                            for i, match in enumerate(batch_result['matches'], 1):
                                with st.expander(f"Match {i}: Similarity {match['similarity_score']:.3f}, Coverage {match['skill_coverage']:.1%}"):
                                    display_match_results(match)
                    else:
                        st.error(f"❌ Batch matching failed: {match_response.text}")
                else:
                    st.success(f"✅ Successfully processed {processed_count} files!")
                
                # Refresh the session state
                load_user_data()
                
            except Exception as e:
                st.error(f"❌ Batch processing failed: {str(e)}")
def matching_tab():
    """Enhanced matching tab with better visualizations"""
    st.header("🔍 Resume Matching")
    
    # Debug: Check the structure of resumes
    st.write("Debug - Resume structure:", st.session_state.resumes[0] if st.session_state.resumes else "No resumes")
    
    if not st.session_state.resumes or not st.session_state.jds:
        st.warning("Please upload at least one resume and one job description first.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        resume_option = st.selectbox(
            "Select Resume",
            options=[f"Resume {i+1}" for i in range(len(st.session_state.resumes))],
            format_func=lambda x: f"{x} - {st.session_state.resumes[int(x.split()[1])-1].get('email', st.session_state.resumes[int(x.split()[1])-1].get('filename', 'Unknown'))}"
        )
    
    with col2:
        jd_option = st.selectbox(
            "Select Job Description",
            options=[f"JD {i+1}" for i in range(len(st.session_state.jds))],
            format_func=lambda x: f"{x} - {st.session_state.jds[int(x.split()[1])-1].get('title', st.session_state.jds[int(x.split()[1])-1].get('filename', 'Unknown Position'))}"
        )
    
    if st.button("🚀 Match Resume to JD", type="primary"):
        resume_idx = int(resume_option.split()[1]) - 1
        jd_idx = int(jd_option.split()[1]) - 1
        
        # Try different possible keys for ID
        resume_obj = st.session_state.resumes[resume_idx]
        jd_obj = st.session_state.jds[jd_idx]
        
        # Check what keys are available
        st.write("Resume keys:", resume_obj.keys())
        st.write("JD keys:", jd_obj.keys())
        
        # Try common ID field names
        resume_id = resume_obj.get("id") or resume_obj.get("_id") or resume_obj.get("resume_id")
        jd_id = jd_obj.get("id") or jd_obj.get("_id") or jd_obj.get("jd_id")
        
        if not resume_id or not jd_id:
            st.error("Could not find ID fields in the objects. Please check the API response structure.")
            return
        
        with st.spinner("Analyzing match..."):
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                resp = requests.post(
                    f"{API_BASE_URL}/match/",
                    params={"resume_id": resume_id, "jd_id": jd_id},
                    headers=headers
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    st.session_state.matches.append(result)
                    st.success("✅ Matching completed!")
                    
                    # Display results
                    display_match_results(result)
                else:
                    st.error(f"❌ Matching failed: {resp.text}")
            except Exception as e:
                st.error(f"❌ Matching failed: {str(e)}")
    
    # Batch matching section
    st.subheader("🔄 Batch Matching")
    st.info("Match all resumes against all job descriptions at once")
    
    if len(st.session_state.resumes) > 0 and len(st.session_state.jds) > 0:
        if st.button("🚀 Perform Batch Matching", type="secondary"):
            with st.spinner("Performing batch matching..."):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    
                    # Get all resume and JD IDs with fallback for different field names
                    resume_ids = []
                    for resume in st.session_state.resumes:
                        resume_id = resume.get("id") or resume.get("_id") or resume.get("resume_id")
                        if resume_id:
                            resume_ids.append(resume_id)
                    
                    jd_ids = []
                    for jd in st.session_state.jds:
                        jd_id = jd.get("id") or jd.get("_id") or jd.get("jd_id")
                        if jd_id:
                            jd_ids.append(jd_id)
                    
                    if not resume_ids or not jd_ids:
                        st.error("Could not extract IDs from resumes or job descriptions")
                        return
                    
                    batch_match_data = {
                        "resume_ids": resume_ids,
                        "jd_ids": jd_ids,
                        "weights": {
                            "skill_coverage": 0.4,
                            "similarity": 0.4,
                            "density": 0.2
                        }
                    }
                    
                    response = requests.post(
                        f"{API_BASE_URL}/batch/match",
                        json=batch_match_data,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        batch_result = response.json()
                        matches_performed = batch_result['total_matches']
                        st.success(f"✅ Batch matching completed! {matches_performed} matches performed.")
                        
                        # Display all batch match results
                        if batch_result['matches']:
                            st.subheader("📊 All Batch Match Results")
                            for i, match in enumerate(batch_result['matches'], 1):
                                with st.expander(f"Match {i}: Similarity {match['similarity_score']:.3f}, Coverage {match['skill_coverage']:.1%}"):
                                    display_match_results(match)
                    else:
                        st.error(f"❌ Batch matching failed: {response.text}")
                except Exception as e:
                    st.error(f"❌ Batch matching failed: {str(e)}")
    else:
        st.warning("Need at least one resume and one job description for batch matching.")

def display_match_results(result):
    """Display match results with enhanced visualizations"""
    st.subheader("📊 Match Results")
    
    # Key metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        similarity = result.get("similarity_score", 0)
        st.metric(
            "Semantic Similarity",
            f"{similarity:.2f}",
            help="How well the resume content matches the job description"
        )
    
    with col2:
        coverage = result.get("skill_coverage", 0)
        st.metric(
            "Skill Coverage",
            f"{coverage*100:.0f}%",
            help="Percentage of required skills found in resume"
        )
    
    with col3:
        density = result.get("skill_density", 0)
        st.metric(
            "Skill Density",
            f"{density:.2f}",
            help="Relevance of resume skills to the job"
        )
    
    # Radar chart for skills
    st.subheader("🎯 Skills Analysis")
    
    matching_skills = result.get("matching_skills", [])
    missing_skills = result.get("missing_skills", [])
    
    if matching_skills or missing_skills:
        # Create radar chart
        categories = ["Semantic Similarity", "Skill Coverage", "Skill Density"]
        values = [
            result.get("similarity_score", 0),
            result.get("skill_coverage", 0),
            result.get("skill_density", 0)
        ]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Match Score',
            line_color='blue'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )),
            showlegend=True,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Skills breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Matching Skills")
        if matching_skills:
            for skill in matching_skills:
                st.success(f"• {skill}")
        else:
            st.info("No matching skills found")
    
    with col2:
        st.subheader("❌ Missing Skills")
        if missing_skills:
            for skill in missing_skills:
                st.error(f"• {skill}")
        else:
            st.success("All required skills are present!")
    
    # Explanation
    st.subheader("📝 Analysis")
    explanation = result.get("explanation", "")
    st.info(explanation)

def analytics_tab():
    """Analytics tab with detailed insights"""
    st.header("📈 Analytics & Insights")
    
    if not st.session_state.matches:
        st.info("Perform some matches to see analytics")
        return
    
    # Match history
    st.subheader("📊 Match History")
    
    match_data = []
    for i, match in enumerate(st.session_state.matches):
        match_data.append({
            "Match #": i + 1,
            "Similarity": match.get("similarity_score", 0),
            "Coverage": match.get("skill_coverage", 0),
            "Density": match.get("skill_density", 0)
        })
    
    if match_data:
        df = pd.DataFrame(match_data)
        st.dataframe(df, use_container_width=True)
        
        # Trends chart
        fig = px.line(df, x="Match #", y=["Similarity", "Coverage", "Density"],
                     title="Match Performance Trends")
        st.plotly_chart(fig, use_container_width=True)

def settings_tab():
    """Settings tab for user preferences"""
    st.header("⚙️ Settings")
    
    st.subheader("User Information")
    if st.session_state.user:
        st.write(f"**Username:** {st.session_state.user['username']}")
        st.write(f"**Email:** {st.session_state.user['email']}")
        st.write(f"**Account Created:** {st.session_state.user['created_at']}")
        st.write(f"**Admin:** {'Yes' if st.session_state.user['is_admin'] else 'No'}")
    
    st.subheader("API Configuration")
    st.info(f"API Base URL: {API_BASE_URL}")
    
    st.subheader("System Information")
    st.write("**Version:** 2.0.0")
    st.write("**Features:** Database integration, Authentication, Enhanced UI")

def main():
    """Main application function"""
    init_session_state()
    
    if not st.session_state.authenticated:
        login_page()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()