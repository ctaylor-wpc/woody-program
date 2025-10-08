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
    
    # Check if we need to migrate the old schema
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
    table_exists = c.fetchone()
    
    if table_exists:
        # Check current schema
        c.execute("PRAGMA table_info(projects)")
        columns = [col[1] for col in c.fetchall()]
        
        # If old schema detected, migrate
        if 'house' not in columns:
            migrate_database(conn, c)
    else:
        # Create new table with updated schema
        c.execute('''CREATE TABLE IF NOT EXISTS projects
                     (id TEXT PRIMARY KEY,
                      name TEXT NOT NULL,
                      overall_status TEXT,
                      house TEXT,
                      plant_shape TEXT,
                      water_status TEXT,
                      pest_presence TEXT,
                      disease_presence TEXT,
                      quantity TEXT,
                      root_structure TEXT,
                      nutrient_status TEXT,
                      pest_type TEXT,
                      disease_type TEXT,
                      action_required TEXT,
                      priority TEXT,
                      retail_ready TEXT,
                      retail_timeline TEXT,
                      header_image_id TEXT,
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

def migrate_database(conn, c):
    """Migrate old database schema to new schema"""
    try:
        # Get all existing projects
        c.execute('SELECT * FROM projects')
        old_projects = c.fetchall()
        
        # Rename old table
        c.execute('ALTER TABLE projects RENAME TO projects_old')
        
        # Create new table with updated schema
        c.execute('''CREATE TABLE projects
                     (id TEXT PRIMARY KEY,
                      name TEXT NOT NULL,
                      overall_status TEXT,
                      house TEXT,
                      plant_shape TEXT,
                      water_status TEXT,
                      pest_presence TEXT,
                      disease_presence TEXT,
                      quantity TEXT,
                      root_structure TEXT,
                      nutrient_status TEXT,
                      pest_type TEXT,
                      disease_type TEXT,
                      action_required TEXT,
                      priority TEXT,
                      retail_ready TEXT,
                      retail_timeline TEXT,
                      header_image_id TEXT,
                      last_updated TEXT)''')
        
        # Migrate data
        for old_proj in old_projects:
            # Old schema: id, name, overall_status, overall_health, root_growth, pest_presence,
            #             disease_presence, water_level, soil_quality, greenhouse_location,
            #             next_steps, retail_availability, last_updated
            
            new_proj = (
                old_proj[0],  # id
                old_proj[1],  # name
                old_proj[2],  # overall_status
                old_proj[9] if len(old_proj) > 9 else 'TBD',  # house (from greenhouse_location)
                'TBD',  # plant_shape
                old_proj[7] if len(old_proj) > 7 else 'TBD',  # water_status (from water_level)
                old_proj[5] if len(old_proj) > 5 else 'None',  # pest_presence
                old_proj[6] if len(old_proj) > 6 else 'None',  # disease_presence
                'TBD',  # quantity
                old_proj[4] if len(old_proj) > 4 else 'TBD',  # root_structure (from root_growth)
                old_proj[8] if len(old_proj) > 8 else 'TBD',  # nutrient_status (from soil_quality)
                '',  # pest_type
                '',  # disease_type
                old_proj[10] if len(old_proj) > 10 else 'TBD',  # action_required (from next_steps)
                'Medium',  # priority (default)
                old_proj[11] if len(old_proj) > 11 else 'Not yet available',  # retail_ready
                'TBD',  # retail_timeline
                None,  # header_image_id
                old_proj[12] if len(old_proj) > 12 else datetime.now().strftime('%Y-%m-%d')  # last_updated
            )
            
            c.execute('''INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      new_proj)
        
        # Drop old table
        c.execute('DROP TABLE projects_old')
        conn.commit()
        
        print(f"Successfully migrated {len(old_projects)} projects to new schema")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {str(e)}")
        raise

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
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        return file.get('id')
    except Exception as e:
        st.error(f"Error uploading to Google Drive: {str(e)}")
        return None

def delete_photo_from_drive(file_id):
    """Delete photo from Google Drive"""
    try:
        service = get_google_drive_service()
        if not service:
            return False
        
        service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting from Google Drive: {str(e)}")
        return False

def get_photo_url_from_drive(file_id):
    """Generate viewable URL for photo from Google Drive file ID"""
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"

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
    c.execute('''INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              project_data)
    conn.commit()
    conn.close()

def update_project_status(project_id, status_data):
    """Update project status fields"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    c.execute('''UPDATE projects SET 
                 overall_status = ?,
                 house = ?,
                 plant_shape = ?,
                 water_status = ?,
                 pest_presence = ?,
                 disease_presence = ?,
                 quantity = ?,
                 root_structure = ?,
                 nutrient_status = ?,
                 pest_type = ?,
                 disease_type = ?,
                 action_required = ?,
                 priority = ?,
                 retail_ready = ?,
                 retail_timeline = ?,
                 last_updated = ?
                 WHERE id = ?''',
              (*status_data, project_id))
    conn.commit()
    conn.close()

def update_project_header_image(project_id, image_id):
    """Update project header image"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    c.execute('UPDATE projects SET header_image_id = ? WHERE id = ?', (image_id, project_id))
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

def delete_photo(photo_id):
    """Delete photo record from database"""
    conn = sqlite3.connect('nursery.db')
    c = conn.cursor()
    c.execute('DELETE FROM photos WHERE id = ?', (photo_id,))
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
            ('hydrangea-little-lime-2025', 'Hydrangea Little Lime 2025', 'Healthy',
             'House 3', 'Rounded', 'Adequate', 'None', 'None',
             '45 units', 'Excellent', 'Good', '', '',
             'Monitor for aphids', 'Medium', 'Available', 'Ready now',
             None, '2025-10-05'),
            ('knockout-roses-spring-2025', 'Knockout Roses Spring 2025', 'Needs Attention',
             'House 1', 'Bushy', 'Slightly dry', 'Little', 'None',
             '30 units', 'Moderate', 'Fair', 'Aphids', '',
             'Apply aphid treatment, increase watering', 'High', 'Not yet available', '2-3 weeks',
             None, '2025-10-06')
        ]
        for project in sample_projects:
            add_project(project)
        
        add_comment('hydrangea-little-lime-2025', 'Sarah M.', 'Plants looking great! Color is coming in nicely.')
        add_comment('hydrangea-little-lime-2025', 'Mike T.', 'Adjusted watering schedule. Monitoring closely.')
        add_comment('knockout-roses-spring-2025', 'Mike T.', 'Spotted some aphids on lower leaves. Planning treatment for tomorrow.')

# Home page with project cards
def show_home_page():
    st.title("🌱 Nursery Project Manager")
    st.markdown("Track and manage plant projects")
    st.markdown("---")
    
    # Add New Project Button
    if st.button("➕ Create New Project", use_container_width=True):
        st.session_state.show_new_project_form = True
    
    # Show new project form if flag is set
    if st.session_state.get('show_new_project_form', False):
        with st.expander("📝 New Project Form", expanded=True):
            new_project_name = st.text_input("Project Name", key="new_proj_name")
            new_project_id = st.text_input("Project ID (lowercase, no spaces)", key="new_proj_id", 
                                          help="Example: roses-2025 or hydrangea-batch-3")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Create Project", use_container_width=True):
                    if new_project_name and new_project_id:
                        existing = get_project_by_id(new_project_id)
                        if existing:
                            st.error("Project ID already exists! Choose a different ID.")
                        else:
                            new_project_data = (
                                new_project_id,
                                new_project_name,
                                'Healthy',
                                'TBD', 'TBD', 'TBD', 'None', 'None',
                                'TBD', 'TBD', 'TBD', '', '',
                                'Initial planting and monitoring',
                                'Medium',
                                'Not yet available',
                                'TBD',
                                None,
                                datetime.now().strftime('%Y-%m-%d')
                            )
                            add_project(new_project_data)
                            st.success(f"Project '{new_project_name}' created!")
                            st.session_state.show_new_project_form = False
                            st.rerun()
                    else:
                        st.warning("Please fill in both Project Name and Project ID")
            
            with col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.show_new_project_form = False
                    st.rerun()
    
    st.markdown("---")
    st.subheader("📋 All Projects")
    
    # Display projects as cards
    projects = get_all_projects()
    
    if len(projects) == 0:
        st.info("No projects found. Create your first project!")
        return
    
    # Create 3 columns for cards
    cols = st.columns(3)
    
    for idx, project in enumerate(projects):
        proj_id = project[0]
        name = project[1]
        status = project[2]
        last_updated = project[-1]
        
        with cols[idx % 3]:
            # Card styling
            status_emoji = "🟢" if status == "Healthy" else "🟡" if status == "Needs Attention" else "🔴"
            
            card_html = f"""
            <div style="background-color: #54592C; padding: 20px; border-radius: 10px; margin-bottom: 20px; min-height: 200px;">
                <h3 style="color: white; margin-top: 0;">{name}</h3>
                <p style="color: #E8E8E8; font-size: 1.1em; margin: 10px 0;">
                    {status_emoji} <strong>{status}</strong>
                </p>
                <p style="color: #C8C8C8; font-size: 0.9em; margin-top: 20px;">
                    Last updated: {last_updated}
                </p>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            if st.button("View Project", key=f"view_{proj_id}", use_container_width=True):
                st.session_state.current_project = proj_id
                st.rerun()

# Project detail page
def show_project_page(project_id):
    # Back button
    if st.button("← Back to All Projects"):
        st.session_state.current_project = None
        st.rerun()
    
    # Get project
    project = get_project_by_id(project_id)
    if not project:
        st.error("Project not found")
        return
    
    # Unpack project data
    (proj_id, name, overall_status, house, plant_shape, water_status, 
     pest_presence, disease_presence, quantity, root_structure, nutrient_status,
     pest_type, disease_type, action_required, priority, retail_ready,
     retail_timeline, header_image_id, last_updated) = project
    
    # Header image section
    if header_image_id:
        try:
            header_url = get_photo_url_from_drive(header_image_id)
            st.image(header_url, use_container_width=True)
        except:
            st.info("Header image not available")
    
    # Upload header image option
    with st.expander("📸 Upload/Change Header Image"):
        header_file = st.file_uploader("Choose header image", type=['jpg', 'jpeg', 'png'], key="header_upload")
        if st.button("Set as Header Image"):
            if header_file:
                file_bytes = header_file.read()
                filename = f"{proj_id}_header_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{header_file.name}"
                google_drive_id = upload_photo_to_drive(file_bytes, filename, header_file.type)
                
                if google_drive_id:
                    # Delete old header image if exists
                    if header_image_id:
                        delete_photo_from_drive(header_image_id)
                    
                    update_project_header_image(proj_id, google_drive_id)
                    st.success("Header image updated!")
                    st.rerun()
    
    st.markdown("---")
    
    # Project title and status
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
                st.session_state.house,
                st.session_state.plant_shape,
                st.session_state.water_status,
                st.session_state.pest_presence,
                st.session_state.disease_presence,
                st.session_state.quantity,
                st.session_state.root_structure,
                st.session_state.nutrient_status,
                st.session_state.pest_type,
                st.session_state.disease_type,
                st.session_state.action_required,
                st.session_state.priority,
                st.session_state.retail_ready,
                st.session_state.retail_timeline,
                datetime.now().strftime('%Y-%m-%d')
            )
            update_project_status(proj_id, status_data)
            st.success("Status updated successfully!")
            st.session_state.edit_mode = False
            st.rerun()
        else:
            st.session_state.edit_mode = True
            st.rerun()
    
    # Three column layout
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Left Column")
        if st.session_state.edit_mode:
            st.session_state.house = st.text_input("House:", house)
            st.session_state.plant_shape = st.text_input("Plant Shape:", plant_shape)
            st.session_state.water_status = st.text_input("Water Status:", water_status)
            st.session_state.pest_presence = st.selectbox("Pest Presence:", 
                ["None", "Little", "Moderate", "High"], 
                index=["None", "Little", "Moderate", "High"].index(pest_presence) if pest_presence in ["None", "Little", "Moderate", "High"] else 0)
            st.session_state.disease_presence = st.selectbox("Disease Presence:", 
                ["None", "Little", "Moderate", "High"], 
                index=["None", "Little", "Moderate", "High"].index(disease_presence) if disease_presence in ["None", "Little", "Moderate", "High"] else 0)
        else:
            st.markdown(f"**House:** {house}")
            st.markdown(f"**Plant Shape:** {plant_shape}")
            st.markdown(f"**Water Status:** {water_status}")
            st.markdown(f"**Pest Presence:** {pest_presence}")
            st.markdown(f"**Disease Presence:** {disease_presence}")
    
    with col2:
        st.markdown("### Center Column")
        if st.session_state.edit_mode:
            st.session_state.quantity = st.text_input("Quantity:", quantity)
            st.session_state.root_structure = st.text_input("Root Structure:", root_structure)
            st.session_state.nutrient_status = st.text_input("Nutrient Status:", nutrient_status)
            st.session_state.pest_type = st.text_input("Pest Type:", pest_type)
            st.session_state.disease_type = st.text_input("Disease Type:", disease_type)
        else:
            st.markdown(f"**Quantity:** {quantity}")
            st.markdown(f"**Root Structure:** {root_structure}")
            st.markdown(f"**Nutrient Status:** {nutrient_status}")
            st.markdown(f"**Pest Type:** {pest_type}")
            st.markdown(f"**Disease Type:** {disease_type}")
    
    with col3:
        st.markdown("### Right Column")
        if st.session_state.edit_mode:
            st.session_state.overall_status = st.selectbox("Overall Status:", 
                ["Healthy", "Needs Attention", "Critical"], 
                index=["Healthy", "Needs Attention", "Critical"].index(overall_status) if overall_status in ["Healthy", "Needs Attention", "Critical"] else 0)
            st.session_state.action_required = st.text_area("Action Required:", action_required, height=100)
            st.session_state.priority = st.selectbox("Priority:", 
                ["Low", "Medium", "High", "Urgent"],
                index=["Low", "Medium", "High", "Urgent"].index(priority) if priority in ["Low", "Medium", "High", "Urgent"] else 1)
            st.session_state.retail_ready = st.text_input("Retail Ready:", retail_ready)
            st.session_state.retail_timeline = st.text_input("Retail Timeline:", retail_timeline)
        else:
            st.markdown(f"**Overall Status:** {overall_status}")
            st.markdown(f"**Action Required:** {action_required}")
            st.markdown(f"**Priority:** {priority}")
            st.markdown(f"**Retail Ready:** {retail_ready}")
            st.markdown(f"**Retail Timeline:** {retail_timeline}")
    
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
                file_bytes = uploaded_file.read()
                filename = f"{proj_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
                google_drive_id = upload_photo_to_drive(file_bytes, filename, uploaded_file.type)
                
                if google_drive_id:
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
                    photo_url = get_photo_url_from_drive(google_drive_id)
                    st.image(photo_url, use_container_width=True)
                    st.caption(f"**{caption}**")
                    st.caption(f"*{user} • {date}*")
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_{photo_id}"):
                        if delete_photo_from_drive(google_drive_id):
                            delete_photo(photo_id)
                            st.success("Photo deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete photo")
                except Exception as e:
                    st.error(f"Error loading photo")
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
    
    # Display comments with green background
    comments = get_project_comments(proj_id)
    if comments:
        for comment in comments:
            comment_id, project_id, user, text, date = comment
            st.markdown(f"""
            <div style="border-left: 4px solid #3d4221; padding: 15px; margin: 10px 0; background-color: #54592C; border-radius: 5px;">
                <strong style="color: white;">{user}</strong> <span style="color: #D8D8D8; font-size: 0.9em;">• {date}</span><br>
                <p style="color: #F0F0F0; margin-top: 8px;">{text}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No comments yet. Start the conversation!")

# Main Streamlit App
def main():
    st.set_page_config(page_title="Nursery Project Manager", page_icon="🌱", layout="wide")
    
    # Initialize database
    init_database()
    seed_sample_data()
    
    # Initialize session state for current project
    if 'current_project' not in st.session_state:
        st.session_state.current_project = None
    
    # Show appropriate page
    if st.session_state.current_project:
        show_project_page(st.session_state.current_project)
    else:
        show_home_page()

if __name__ == "__main__":
    main()