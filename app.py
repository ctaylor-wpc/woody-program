import streamlit as st
import sqlite3
from datetime import datetime
import io
from PIL import Image
import json

# Google Drive imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# ============================================================================
# GOOGLE DRIVE CONFIGURATION
# ============================================================================

def get_service_account_info():
    """
    Reads service account JSON from st.secrets
    """
    sa = st.secrets.get("gcp", {}).get("service_account_json")
    if not sa:
        raise KeyError("Service account JSON not found in secrets")
    if isinstance(sa, str):
        return json.loads(sa)
    return sa

# Your Google Drive folder ID
GOOGLE_DRIVE_FOLDER_ID = '1D6tvx4ApYZeNuLnGre7uTe12qZjEIsjM'

# ============================================================================

# Database initialization
def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    
    # Projects table
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  overall_status TEXT,
                  overall_health INTEGER,
                  root_growth TEXT,
                  pest_presence TEXT,
                  disease_presence TEXT,
                  water_level TEXT,
                  soil_quality TEXT,
                  greenhouse_location TEXT,
                  next_steps TEXT,
                  retail_availability TEXT,
                  last_updated TEXT)''')
    
    # Photos table
    c.execute('''CREATE TABLE IF NOT EXISTS photos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id TEXT,
                  google_drive_id TEXT,
                  caption TEXT,
                  user_name TEXT,
                  date_added TEXT,
                  FOREIGN KEY (project_id) REFERENCES projects(id))''')
    
    # Comments table
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id TEXT,
                  user_name TEXT,
                  comment_text TEXT,
                  date_added TEXT,
                  FOREIGN KEY (project_id) REFERENCES projects(id))''')
    
    conn.commit()
    conn.close()

def get_google_drive_service():
    """Initialize and return Google Drive service"""
    try:
        sa_info = get_service_account_info()
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Error connecting to Google Drive: {str(e)}")
        return None

def upload_photo_to_drive(file_bytes, filename, mime_type='image/jpeg'):
    """Upload photo to Google Drive and return the file ID"""
    try:
        service = get_google_drive_service()
        if not service:
            return None
        
        file_metadata = {
            'name': filename,
            'parents': [GOOGLE_DRIVE_FOLDER_ID]
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype=mime_type,
            resumable=True
        )
        
        # Add supportsAllDrives=True for Shared Drives
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        # Make file publicly readable (optional - remove if you want private files)
        service.permissions().create(
            fileId=file.get('id'),
            body={'type': 'anyone', 'role': 'reader'},
            supportsAllDrives=True
        ).execute()
        
        return file.get('id')
    except Exception as e:
        st.error(f"Error uploading to Google Drive: {str(e)}")
        return None

def get_photo_url_from_drive(file_id):
    """Generate viewable URL for photo from Google Drive file ID"""
    # For Shared Drives, we need to use a different URL format
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"

def download_photo_from_drive(file_id):
    """Download photo from Google Drive"""
    try:
        service = get_google_drive_service()
        if not service:
            return None
        
        # Add supportsAllDrives=True for Shared Drives
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        file_bytes = io.BytesIO()
        downloader = MediaIoBaseDownload(file_bytes, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        file_bytes.seek(0)
        return file_bytes
    except Exception as e:
        st.error(f"Error downloading from Google Drive: {str(e)}")
        return None

# Database query functions
def get_all_projects():
    """Retrieve all projects from database"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    c.execute('SELECT * FROM projects ORDER BY last_updated DESC')
    projects = c.fetchall()
    conn.close()
    return projects

def get_project_by_id(project_id):
    """Get specific project by ID"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    c.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    project = c.fetchone()
    conn.close()
    return project

def add_project(project_data):
    """Add new project to database"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    c.execute('''INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              project_data)
    conn.commit()
    conn.close()

def update_project_status(project_id, status_data):
    """Update project status fields"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    c.execute('''UPDATE projects SET 
                 overall_status = ?,
                 overall_health = ?,
                 root_growth = ?,
                 pest_presence = ?,
                 disease_presence = ?,
                 water_level = ?,
                 soil_quality = ?,
                 greenhouse_location = ?,
                 next_steps = ?,
                 retail_availability = ?,
                 last_updated = ?
                 WHERE id = ?''',
              (*status_data, project_id))
    conn.commit()
    conn.close()

def get_project_photos(project_id):
    """Get all photos for a project"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    c.execute('SELECT * FROM photos WHERE project_id = ? ORDER BY date_added DESC', (project_id,))
    photos = c.fetchall()
    conn.close()
    return photos

def add_photo(project_id, google_drive_id, caption, user_name):
    """Add photo record to database"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    date_added = datetime.now().strftime('%Y-%m-%d')
    c.execute('INSERT INTO photos (project_id, google_drive_id, caption, user_name, date_added) VALUES (?, ?, ?, ?, ?)',
              (project_id, google_drive_id, caption, user_name, date_added))
    conn.commit()
    conn.close()

def get_project_comments(project_id):
    """Get all comments for a project"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    c.execute('SELECT * FROM comments WHERE project_id = ? ORDER BY date_added DESC', (project_id,))
    comments = c.fetchall()
    conn.close()
    return comments

def add_comment(project_id, user_name, comment_text):
    """Add comment to database"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    date_added = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute('INSERT INTO comments (project_id, user_name, comment_text, date_added) VALUES (?, ?, ?, ?)',
              (project_id, user_name, comment_text, date_added))
    conn.commit()
    conn.close()

def seed_sample_data():
    """Add sample projects if database is empty"""
    projects = get_all_projects()
    if len(projects) == 0:
        sample_projects = [
            ('hydrangea-little-lime-2025', 'Hydrangea Little Lime 2025', 'Healthy', 85,
             'Good', 'None', 'None', 'Adequate', 'Excellent', 'GH-3, Row 5',
             'Monitor for aphids, fertilize in 2 weeks', 'Available - 45 units',
             '2025-10-05'),
            ('knockout-roses-spring-2025', 'Knockout Roses Spring 2025', 'Needs Attention', 65,
             'Moderate', 'Minor aphids detected', 'None', 'Slightly dry', 'Good', 'GH-1, Row 2-3',
             'Apply aphid treatment, increase watering', 'Not yet available',
             '2025-10-06')
        ]
        for project in sample_projects:
            add_project(project)
        
        # Add sample comments
        add_comment('hydrangea-little-lime-2025', 'Sarah M.', 'Plants looking great! Color is coming in nicely.')
        add_comment('hydrangea-little-lime-2025', 'Mike T.', 'Adjusted watering schedule. Monitoring closely.')
        add_comment('knockout-roses-spring-2025', 'Mike T.', 'Spotted some aphids on lower leaves. Planning treatment for tomorrow.')

# Main Streamlit App
def main():
    st.set_page_config(page_title="Nursery Project Manager", page_icon="🌱", layout="wide")
    
    # Initialize database
    init_database()
    seed_sample_data()
    
    # Header
    st.title("🌱 Nursery Project Manager")
    st.markdown("Track and manage plant projects")
    
    # Sidebar - Project Selection
    st.sidebar.header("Projects")
    projects = get_all_projects()
    
    if len(projects) == 0:
        st.warning("No projects found. Create your first project!")
        return
    
    # Create project selection dropdown
    project_names = {p[0]: p[1] for p in projects}
    selected_project_id = st.sidebar.selectbox(
        "Select Project",
        options=list(project_names.keys()),
        format_func=lambda x: project_names[x]
    )
    
    # Get selected project
    project = get_project_by_id(selected_project_id)
    if not project:
        st.error("Project not found")
        return
    
    # Unpack project data
    (proj_id, name, overall_status, overall_health, root_growth, pest_presence,
     disease_presence, water_level, soil_quality, greenhouse_location,
     next_steps, retail_availability, last_updated) = project
    
    # Display project info in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Status:** {overall_status}")
    st.sidebar.markdown(f"**Last Updated:** {last_updated}")
    
    # Add New Project Button
    if st.sidebar.button("➕ Create New Project"):
        st.session_state.show_new_project_form = True
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header(name)
    
    with col2:
        status_color = "🟢" if overall_status == "Healthy" else "🟡" if overall_status == "Needs Attention" else "🔴"
        st.markdown(f"## {status_color} {overall_status}")
    
    st.markdown(f"*Last updated: {last_updated}*")
    st.markdown("---")
    
    # Status Section
    st.subheader("📊 Project Status")
    
    # Edit mode toggle
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False
    
    if st.button("✏️ Edit Status" if not st.session_state.edit_mode else "💾 Save Changes"):
        if st.session_state.edit_mode:
            # Save changes
            status_data = (
                st.session_state.overall_status,
                st.session_state.overall_health,
                st.session_state.root_growth,
                st.session_state.pest_presence,
                st.session_state.disease_presence,
                st.session_state.water_level,
                st.session_state.soil_quality,
                st.session_state.greenhouse_location,
                st.session_state.next_steps,
                st.session_state.retail_availability,
                datetime.now().strftime('%Y-%m-%d')
            )
            update_project_status(proj_id, status_data)
            st.success("Status updated successfully!")
            st.session_state.edit_mode = False
            st.rerun()
        else:
            st.session_state.edit_mode = True
            st.rerun()
    
    # Health bar
    st.markdown(f"**Overall Health: {overall_health}%**")
    st.progress(overall_health / 100)
    
    # Status fields
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.edit_mode:
            st.session_state.overall_status = st.selectbox("Overall Status", 
                ["Healthy", "Needs Attention", "Critical"], 
                index=["Healthy", "Needs Attention", "Critical"].index(overall_status) if overall_status in ["Healthy", "Needs Attention", "Critical"] else 0)
            st.session_state.overall_health = st.slider("Overall Health %", 0, 100, overall_health)
            st.session_state.root_growth = st.text_input("Root Growth", root_growth)
            st.session_state.pest_presence = st.text_input("Pest Presence", pest_presence)
            st.session_state.disease_presence = st.text_input("Disease Presence", disease_presence)
        else:
            st.markdown(f"**Root Growth:** {root_growth}")
            st.markdown(f"**Pest Presence:** {pest_presence}")
            st.markdown(f"**Disease Presence:** {disease_presence}")
    
    with col2:
        if st.session_state.edit_mode:
            st.session_state.water_level = st.text_input("Water Level", water_level)
            st.session_state.soil_quality = st.text_input("Soil Quality", soil_quality)
            st.session_state.greenhouse_location = st.text_input("Greenhouse Location", greenhouse_location)
            st.session_state.next_steps = st.text_area("Next Steps", next_steps)
            st.session_state.retail_availability = st.text_input("Retail Availability", retail_availability)
        else:
            st.markdown(f"**Water Level:** {water_level}")
            st.markdown(f"**Soil Quality:** {soil_quality}")
            st.markdown(f"**Greenhouse Location:** {greenhouse_location}")
            st.markdown(f"**Next Steps:** {next_steps}")
            st.markdown(f"**Retail Availability:** {retail_availability}")
    
    st.markdown("---")
    
    # Photos Section
    st.subheader("📷 Photos")
    
    # Photo upload form
    with st.expander("➕ Add New Photo"):
        user_name = st.text_input("Your Name", key="photo_user")
        uploaded_file = st.file_uploader("Choose photo", type=['jpg', 'jpeg', 'png'])
        photo_caption = st.text_input("Caption (optional)", key="photo_caption")
        
        if st.button("Upload Photo"):
            if uploaded_file and user_name:
                # Read file bytes
                file_bytes = uploaded_file.read()
                
                # Upload to Google Drive
                filename = f"{proj_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
                google_drive_id = upload_photo_to_drive(file_bytes, filename, uploaded_file.type)
                
                if google_drive_id:
                    # Save to database
                    add_photo(proj_id, google_drive_id, photo_caption or "No caption", user_name)
                    st.success("Photo uploaded successfully!")
                    st.rerun()
                else:
                    st.error("Failed to upload photo to Google Drive")
            else:
                st.warning("Please provide your name and select a photo")
    
    # Display photos
    photos = get_project_photos(proj_id)
    if photos:
        cols = st.columns(3)
        for idx, photo in enumerate(photos):
            photo_id, project_id, google_drive_id, caption, user, date = photo
            with cols[idx % 3]:
                try:
                    # Try multiple URL formats for better compatibility
                    photo_url = get_photo_url_from_drive(google_drive_id)
                    
                    # Debug info - remove after testing
                    with st.expander("🔍 Debug Info"):
                        st.write(f"File ID: {google_drive_id}")
                        st.write(f"URL: {photo_url}")
                        direct_link = f"https://drive.google.com/file/d/{google_drive_id}/view"
                        st.markdown(f"[Open in Drive]({direct_link})")
                    
                    st.image(photo_url, use_container_width=True)
                    st.caption(f"**{caption}**")
                    st.caption(f"*{user} • {date}*")
                except Exception as e:
                    st.error(f"Error loading photo: {str(e)}")
                    # Provide fallback link
                    direct_link = f"https://drive.google.com/file/d/{google_drive_id}/view"
                    st.markdown(f"[View Photo in Google Drive]({direct_link})")
                    st.caption(f"**{caption}**")
                    st.caption(f"*{user} • {date}*")
    else:
        st.info("No photos yet. Add the first one!")
    
    st.markdown("---")
    
    # Comments Section
    st.subheader("💬 Comments & Updates")
    
    # Add comment form
    with st.expander("➕ Add New Comment"):
        comment_user = st.text_input("Your Name", key="comment_user")
        comment_text = st.text_area("Comment", key="comment_text")
        
        if st.button("Post Comment"):
            if comment_user and comment_text:
                add_comment(proj_id, comment_user, comment_text)
                st.success("Comment added!")
                st.rerun()
            else:
                st.warning("Please provide your name and comment text")
    
    # Display comments
    comments = get_project_comments(proj_id)
    if comments:
        for comment in comments:
            comment_id, project_id, user, text, date = comment
            st.markdown(f"""
            <div style="border-left: 4px solid #4CAF50; padding: 10px; margin: 10px 0; background-color: #f5f5f5; border-radius: 5px;">
                <strong>{user}</strong> <span style="color: #666; font-size: 0.9em;">• {date}</span><br>
                {text}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No comments yet. Start the conversation!")

if __name__ == "__main__":
    main()