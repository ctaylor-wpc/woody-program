import streamlit as st
from datetime import datetime

# --- Mock data ---
projects = [
    {
        "id": 1,
        "name": "Hydrangea Little Lime · 3G",
        "image": "https://placehold.co/300x200?text=Hydrangea",
        "updates": {
            "Overall Health": ("Good", "10/2/25"),
            "Pest Presence": ("None", "10/2/25"),
            "Root Development": ("75%", "10/7/25"),
            "Retail Ready": ("No", "10/5/25"),
            "House": ("5", "10/6/25"),
        },
        "comments": [("Alice Smith", "10/8/25", "Looks good!")],
    },
    {
        "id": 2,
        "name": "Red Maple · 1G",
        "image": "https://placehold.co/300x200?text=Red+Maple",
        "updates": {},
        "comments": [],
    },
    {
        "id": 3,
        "name": "Azalea · 1G",
        "image": "https://placehold.co/300x200?text=Azalea",
        "updates": {},
        "comments": [],
    },
    {
        "id": 4,
        "name": "Enulise · 1G",
        "image": "https://placehold.co/300x200?text=Enulise",
        "updates": {},
        "comments": [],
    },
]

# --- App layout ---
st.set_page_config(page_title="Nursery Project Tracker", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "main"
if "selected_project" not in st.session_state:
    st.session_state.selected_project = None


# --- Functions ---
def go_home():
    st.session_state.page = "main"
    st.session_state.selected_project = None


def select_project(project_id):
    st.session_state.page = "detail"
    st.session_state.selected_project = project_id


# --- Main Page (Gallery) ---
if st.session_state.page == "main":
    st.title("Projects")

    if st.button("➕ Add Project"):
        st.info("Mock app only. No functionality at this time.")

    st.write("")  # spacing

    cols = st.columns(2)
    for i, proj in enumerate(projects):
        with cols[i % 2]:
            st.image(proj["image"], use_container_width=True)
            if st.button(proj["name"], key=proj["id"]):
                select_project(proj["id"])

# --- Detail Page ---
else:
    project = next(p for p in projects if p["id"] == st.session_state.selected_project)

    st.button("← Back to Projects", on_click=go_home)
    st.image(project["image"], use_container_width=True)
    st.subheader(project["name"])

    st.markdown("### Most Recent Updates")

    if project["updates"]:
        for key, (val, date) in project["updates"].items():
            st.write(f"**{key}:** {val}  —  {date}")
    else:
        st.write("_No updates yet_")

    if st.button("Provide Update"):
        st.info("Mock app only. No functionality at this time.")

    st.markdown("---")
    st.markdown("### Comments & Conversation")

    for author, date, text in project["comments"]:
        st.write(f"**{author}** ({date})")
        st.write(text)
        st.write("")

    new_comment = st.text_input("Add comment...")
    if st.button("Submit"):
        st.info("Mock app only. No functionality at this time.")

    st.markdown("---")
    st.markdown("### All Project Photos")
    st.image([project["image"]] * 3, width=120)

    if st.button("Submit Photos"):
        st.info("Mock app only. No functionality at this time.")