import streamlit as st
import json
import os
import hmac
import hashlib
import pandas as pd

# --- File Database Helper Functions ---
st.markdown("""
<style>
.st-emotion-cache-1p1m4ay{
    visibility:hidden
}
</style>
""", unsafe_allow_html=True)
USER_DB_PATH = "user_db.json"
ENROLLMENTS_DB_PATH = "enrollments.json"

def load_data(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_data(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Load file databases.
user_database = load_data(USER_DB_PATH)
enrollments = load_data(ENROLLMENTS_DB_PATH)

# --- Encryption (Deterministic) via HMAC-SHA256 ---
# Make sure to set a strong secret key in your Streamlit secrets.
# Example in .streamlit/secrets.toml:
# [general]
# secret_key = "YOUR_STRONG_SECRET_KEY"
SECRET_KEY = st.secrets["secret_key"]

def encrypt_id(plain_id: str) -> str:
    """
    Returns a deterministic keyed hash of the provided plain_id.
    This hash is used as the key in the user database,
    so that the actual id remains secret.
    """
    return hmac.new(SECRET_KEY.encode(), plain_id.encode(), hashlib.sha256).hexdigest()
def admin_route():
    st.title("Admin Dashboard")

    # Password prompt
    admin_password = st.text_input("Enter Admin Password:", type="password")
    if admin_password != st.secrets["passcode"]:
        st.error("Incorrect password. Access denied.")
        st.stop()

    st.success("Access granted. Welcome, Admin!")

    # View and edit all students
    st.subheader("All Registered Students")
    students_df = pd.DataFrame(
        [{"ID": id, "Name": name} for id, name in user_database.items()]
    )
    edited_students = st.data_editor(students_df, num_rows="dynamic")
    if st.button("Save Changes to Students"):
        # Update user_database based on edits
        user_database.clear()
        for _, row in edited_students.iterrows():
            user_database[row["ID"]] = row["Name"]
        save_data(USER_DB_PATH, user_database)
        st.success("Student data updated successfully!")

    # View and edit teacher-student assignments
    st.subheader("Teacher-Student Assignments")
    assignments = [
        {"Teacher": teacher, "Student": student}
        for teacher, students in enrollments.items()
        for student in students
    ]
    assignments_df = pd.DataFrame(assignments)
    edited_assignments = st.data_editor(assignments_df, num_rows="dynamic")
    if st.button("Save Changes to Assignments"):
        # Update enrollments based on edits
        enrollments.clear()
        for _, row in edited_assignments.iterrows():
            teacher = row["Teacher"]
            student = row["Student"]
            if teacher not in enrollments:
                enrollments[teacher] = []
            enrollments[teacher].append(student)
        save_data(ENROLLMENTS_DB_PATH, enrollments)
        st.success("Assignments updated successfully!")

# --- Bilingual Texts and Sample Teacher Data ---
texts = {
    "English": {
        "page_title": "PLE Youth Enrollment",
        "language_label": "Choose Language",
        "teacher_search_label": "Search for a teacher by name:",
        "teacher_not_found_error": "No teacher found with that search term.",
        "enter_teacher_info": "Displaying all teachers. Use the search box above to filter.",
        "teaches": "Teaches",
        "to_grade": "to grade",
        "enroll_button": "Enroll",
        "cancel_button": "Cancel Enrollment",
        "enroll_success": "Thank you, {name}! You are now enrolled in {teacher}'s class!",
        "enrollment_cancelled": "Enrollment has been cancelled.",
        "register_prompt": "Welcome! Please register by entering the student's English Full name below:",
        "register_button": "Register",
        "logged_in": "Logged in as: {name}",
        "enrolled_label": "Enrolled Students",
        "no_enrollments": "No students enrolled yet.",
        "not_enrolled": "Your name was not found in the enrollment.",
        "name_required": "Please enter your name to register."
    },
    "中文": {
        "page_title": "PLE Youth 教师搜索与注册",
        "language_label": "选择语言",
        "teacher_search_label": "请输入教师姓名搜索：",
        "teacher_not_found_error": "没有匹配的教师。",
        "enter_teacher_info": "正在显示所有教师。使用上方搜索框筛选。",
        "teaches": "授课",
        "to_grade": "年级",
        "enroll_button": "报名",
        "cancel_button": "取消报名",
        "enroll_success": "谢谢, {name}! 你已注册到 {teacher} 的课程！",
        "enrollment_cancelled": "报名已取消。",
        "register_prompt": "欢迎！请通过输入学生的英文（或拼音）全名完成注册：",
        "register_button": "注册",
        "logged_in": "已登录: {name}",
        "enrolled_label": "已报名的学生",
        "no_enrollments": "当前没有报名的学生。",
        "not_enrolled": "未找到你的报名记录。",
        "name_required": "请输入你的名字以注册。"
    }
}

# Sample teacher data (in memory)
teachers = {
    "Alice": {"subject_en": "Mathematics", "subject_zh": "数学", "grade": "8"},
    "Bob": {"subject_en": "Physics", "subject_zh": "物理", "grade": "9"},
    "Charlie": {"subject_en": "History", "subject_zh": "历史", "grade": "10"}
}

# --- (Optional) CSS for Layout ---
st.markdown(
    """
    <style>
    .centered {
        display: flex;
        align-items: center;
        height: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Retrieve Query Param "id" and Process with Encryption ---
params = st.query_params
plain_id = params.get("id", "")
if isinstance(plain_id, list):
    plain_id = plain_id[0]  # In case it's provided as a list

if not plain_id:
    st.error("No user id provided in URL. Please use ?id=your_id")
    st.stop()
if plain_id == "admin":
    admin_route()
else:
    # Convert the provided id into a secure token using encryption.
    secure_id = encrypt_id(plain_id)
    
    # --- Sidebar Language Selector ---
    selected_language = st.sidebar.selectbox("Language / 语言", options=["English", "中文"])
    lang = texts[selected_language]
    
    # --- Update Tab Title Based on Language Selection ---
    st.markdown(f"""
        <script>
            document.title = "{lang['page_title']}";
        </script>
        """, unsafe_allow_html=True)
    
    # --- Registration Check ---
    if secure_id not in user_database:
        st.title(lang["page_title"])
        st.write(lang["register_prompt"])
        new_user_name = st.text_input(lang["name_required"], key="register_input")
        if st.button(lang["register_button"]):
            if new_user_name:
                # Register user: record the secure id (not the plain one) mapped to the entered name.
                user_database[secure_id] = new_user_name
                save_data(USER_DB_PATH, user_database)
                st.rerun()  # Reload the app so the user is now "logged in."
            else:
                st.error(lang["name_required"])
        st.stop()
    
    # User is registered: get the registered user name.
    user_name = user_database[secure_id]
    st.sidebar.write(lang["logged_in"].format(name=user_name))
    
    # --- Main Application: Teacher Search and Enrollment ---
    st.title(lang["page_title"])
    
    # Teacher filter input.
    teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter")
    
    # Filter the teachers (case-insensitive).
    filtered_teachers = {
        name: info for name, info in teachers.items()
        if teacher_filter.lower() in name.lower()
    }
    
    if teacher_filter.strip() == "":
        st.info(lang["enter_teacher_info"])
    
    if not filtered_teachers:
        st.error(lang["teacher_not_found_error"])
    else:
        for teacher_name, teacher_info in filtered_teachers.items():
            st.header(teacher_name)
    
            # Initialize enrollment list for teacher if necessary.
            if teacher_name not in enrollments:
                enrollments[teacher_name] = []
                save_data(ENROLLMENTS_DB_PATH, enrollments)
            
            # Display teacher description.
            if selected_language == "English":
                description = (
                    f"{lang['teaches']} **{teacher_info['subject_en']}** "
                    f"{lang['to_grade']} **{teacher_info['grade']}**."
                )
            else:
                description = (
                    f"{lang['teaches']} **{teacher_info['subject_zh']}**，"
                    f"{lang['to_grade']} **{teacher_info['grade']}**."
                )
            st.write(description)
    
            # Enrollment actions: Use two columns for buttons.
            col1, col2 = st.columns(2)
            with col1:
                enroll_clicked = st.button(lang["enroll_button"], key=f"enroll_button_{teacher_name}")
            with col2:
                cancel_clicked = st.button(lang["cancel_button"], key=f"cancel_button_{teacher_name}")
    
            # Process enrollment.
            if enroll_clicked:
                if user_name not in enrollments[teacher_name]:
                    enrollments[teacher_name].append(user_name)
                    save_data(ENROLLMENTS_DB_PATH, enrollments)
                st.success(lang["enroll_success"].format(name=user_name, teacher=teacher_name))
    
            # Process cancellation.
            if cancel_clicked:
                if user_name in enrollments[teacher_name]:
                    enrollments[teacher_name].remove(user_name)
                    save_data(ENROLLMENTS_DB_PATH, enrollments)
                    st.info(lang["enrollment_cancelled"])
                else:
                    st.error(lang["not_enrolled"])
    
            # Display enrolled students using an expander.
            with st.expander(lang["enrolled_label"]):
                if enrollments[teacher_name]:
                    for s in enrollments[teacher_name]:
                        st.write(f"- {s}")
                else:
                    st.write(lang["no_enrollments"])
            st.markdown("---")
