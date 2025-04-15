import streamlit as st
import json
import os
import hmac
import hashlib
import pandas as pd

# --- File Database Helper Functions ---
# Hide default Streamlit elements if needed (keeping as is)
st.markdown("""
<style>
.st-emotion-cache-1p1m4ay{
    visibility:hidden
}
/* Optional: Hide the 'Fork' button on deployed apps */
/* .st-emotion-cache-zq5wmm.e1f1d6gn0 { visibility: hidden; } */
/* Optional: Hide the GitHub icon */
/* .st-emotion-cache-1wbqy5e.e1f1d6gn3 { visibility: hidden; } */
</style>
""", unsafe_allow_html=True)

USER_DB_PATH = "user_db.json"
ENROLLMENTS_DB_PATH = "enrollments.json"
TEACHERS_DB_PATH = "teachers.json" # New path for teacher data

def load_data(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                # Handle empty file case
                content = f.read()
                if not content:
                    return {}
                return json.loads(content)
            except json.JSONDecodeError:
                st.error(f"Error decoding JSON from {path}. Returning empty data.")
                return {}
    return {}

def save_data(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving data to {path}: {e}")


# Load file databases.
user_database = load_data(USER_DB_PATH)
enrollments = load_data(ENROLLMENTS_DB_PATH)
teachers_database = load_data(TEACHERS_DB_PATH) # Load teacher data

# --- Encryption (Deterministic) via HMAC-SHA256 ---
# Ensure secret_key is set in Streamlit secrets ([secrets] section)
if "secret_key" not in st.secrets:
    st.error("`secret_key` not found in Streamlit secrets. Please add it to `.streamlit/secrets.toml`")
    st.stop()
SECRET_KEY = st.secrets["secret_key"]

def encrypt_id(plain_id: str) -> str:
    """
    Returns a deterministic keyed hash of the provided plain_id.
    This hash is used as the key in the user database,
    so that the actual id remains secret.
    """
    return hmac.new(SECRET_KEY.encode(), plain_id.encode(), hashlib.sha256).hexdigest()

# --- Admin Route ---
def admin_route():
    global user_database, enrollments, teachers_database # Allow modification of global vars

    st.title("Admin Dashboard")

    # Password prompt
    if "passcode" not in st.secrets:
        st.error("Admin `passcode` not found in Streamlit secrets. Cannot proceed.")
        st.stop()
    admin_password = st.text_input("Enter Admin Password:", type="password", key="admin_pw")
    if not admin_password:
        st.warning("Please enter the admin password.")
        st.stop()
    if admin_password != st.secrets["passcode"]:
        st.error("Incorrect password. Access denied.")
        st.stop()

    st.success("Access granted. Welcome, Admin!")

    # **Refresh Button**
    if st.button("Refresh Data from Files"):
        # Explicitly reload data when refresh is clicked
        user_database = load_data(USER_DB_PATH)
        enrollments = load_data(ENROLLMENTS_DB_PATH)
        teachers_database = load_data(TEACHERS_DB_PATH)
        st.rerun()

    st.markdown("---") # Separator

    # --- Manage Teachers ---
    st.subheader("Manage Teachers")
    st.markdown("Add, edit, or remove teachers here. The 'Teacher Name' will be used as the unique identifier.")

    # Prepare teacher data for data_editor
    # The database stores it as { "Name": {"subject_en": ..., "subject_zh": ..., "grade": ...} }
    # We need to convert it to a list of dicts or DataFrame for st.data_editor
    teachers_list = []
    for name, details in teachers_database.items():
        teachers_list.append({
            "Teacher Name": name,
            "Subject (English)": details.get("subject_en", ""),
            "Subject (Chinese)": details.get("subject_zh", ""),
            "Grade": details.get("grade", "")
        })

    if not teachers_list:
        # Provide default structure if empty
        teachers_df = pd.DataFrame(columns=["Teacher Name", "Subject (English)", "Subject (Chinese)", "Grade"])
    else:
        teachers_df = pd.DataFrame(teachers_list)

    # Use st.data_editor for managing teachers
    edited_teachers_df = st.data_editor(
        teachers_df,
        num_rows="dynamic",
        key="teacher_editor",
        # Make Teacher Name column required maybe? - data_editor doesn't directly support this yet
        column_config={
             "Teacher Name": st.column_config.TextColumn(required=True),
             # Add more column configs if needed (e.g., specific types)
        }
    )

    if st.button("Save Changes to Teachers"):
        new_teachers_database = {}
        error_occurred = False
        seen_names = set()
        for index, row in edited_teachers_df.iterrows():
            name = row["Teacher Name"]
            # Basic validation: Ensure name is not empty and is unique
            if not name or pd.isna(name) or str(name).strip() == "":
                st.error(f"Row {index+1}: Teacher Name cannot be empty.")
                error_occurred = True
                continue
            name = str(name).strip() # Clean whitespace
            if name in seen_names:
                 st.error(f"Row {index+1}: Duplicate Teacher Name '{name}' found. Names must be unique.")
                 error_occurred = True
                 continue
            seen_names.add(name)

            new_teachers_database[name] = {
                "subject_en": str(row["Subject (English)"]) if pd.notna(row["Subject (English)"]) else "",
                "subject_zh": str(row["Subject (Chinese)"]) if pd.notna(row["Subject (Chinese)"]) else "",
                "grade": str(row["Grade"]) if pd.notna(row["Grade"]) else ""
            }

        if not error_occurred:
            try:
                save_data(TEACHERS_DB_PATH, new_teachers_database)
                teachers_database = new_teachers_database # Update in-memory dict
                st.success("Teacher data updated successfully!")
                # Optional: st.rerun() to reflect changes immediately if needed,
                # but often better to let user continue edits unless confirmation is final.
            except Exception as e:
                 st.error(f"Failed to save teacher data: {e}")
        else:
            st.warning("Please fix the errors listed above before saving.")


    st.markdown("---") # Separator

    # --- View and edit all students (Existing Code) ---
    st.subheader("All Registered Students")
    students_list = []
    for user_id, name in user_database.items():
         students_list.append({"Encrypted ID": user_id, "Name": name}) # Use Encrypted ID

    if not students_list:
        students_df = pd.DataFrame(columns=["Encrypted ID", "Name"])
    else:
        students_df = pd.DataFrame(students_list)

    # Display student data (read-only might be safer unless editing names is intended)
    st.dataframe(students_df, use_container_width=True, hide_index=True)
    # Optional: Add deletion functionality if needed, but be careful with dependencies.
    # st.info("Editing student names directly is currently disabled to maintain consistency.")
    # If editing is required:
    # edited_students = st.data_editor(students_df, num_rows="dynamic", key="student_editor", disabled=["Encrypted ID"])
    # if st.button("Save Changes to Students"):
    #     new_user_database = {}
    #     for _, row in edited_students.iterrows():
    #         if row["Encrypted ID"] and row["Name"]: # Basic check
    #             new_user_database[row["Encrypted ID"]] = row["Name"]
    #     save_data(USER_DB_PATH, new_user_database)
    #     user_database = new_user_database # Update in-memory
    #     st.success("Student data updated successfully!")
    #     st.rerun()


    st.markdown("---") # Separator

    # --- View and edit teacher-student assignments (Existing Code) ---
    st.subheader("Teacher-Student Assignments")
    assignments = []
    for teacher, students in enrollments.items():
        for student in students:
            assignments.append({"Teacher": teacher, "Student": student})

    if not assignments:
        assignments_df = pd.DataFrame(columns=["Teacher", "Student"])
    else:
         assignments_df = pd.DataFrame(assignments)


    edited_assignments = st.data_editor(
        assignments_df,
        num_rows="dynamic",
        key="assignment_editor",
        column_config={
            # If you have many teachers/students, dropdowns might be better
            # "Teacher": st.column_config.SelectboxColumn("Teacher", options=list(teachers_database.keys()), required=True),
            # "Student": st.column_config.SelectboxColumn("Student", options=list(user_database.values()), required=True)
            # For now, keep as text input for simplicity
             "Teacher": st.column_config.TextColumn(required=True),
             "Student": st.column_config.TextColumn(required=True),
        }
        )

    if st.button("Save Changes to Assignments"):
        new_enrollments = {}
        error_occurred = False
        for index, row in edited_assignments.iterrows():
            teacher = row["Teacher"]
            student = row["Student"]

            # Basic validation
            if not teacher or pd.isna(teacher) or str(teacher).strip() == "":
                 st.error(f"Row {index+1}: Teacher cannot be empty in assignments.")
                 error_occurred = True
                 continue
            if not student or pd.isna(student) or str(student).strip() == "":
                 st.error(f"Row {index+1}: Student cannot be empty in assignments.")
                 error_occurred = True
                 continue

            teacher = str(teacher).strip()
            student = str(student).strip()

            # Advanced Validation (Optional but Recommended):
            # Check if teacher exists in teachers_database
            if teacher not in teachers_database:
                st.warning(f"Row {index+1}: Teacher '{teacher}' does not exist in the teacher database. Assignment kept, but please verify.")
                # Optionally set error_occurred = True if you want to block saving non-existent teachers

            # Check if student exists in user_database (by name)
            if student not in user_database.values():
                 st.warning(f"Row {index+1}: Student '{student}' does not exist in the user database. Assignment kept, but please verify.")
                 # Optionally set error_occurred = True

            # Add to structure
            if teacher not in new_enrollments:
                new_enrollments[teacher] = []
            # Avoid duplicate enrollments for the same student with the same teacher
            if student not in new_enrollments[teacher]:
                new_enrollments[teacher].append(student)

        if not error_occurred:
            try:
                save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                enrollments = new_enrollments # Update in-memory
                st.success("Assignments updated successfully!")
                # st.rerun() # Refresh page to show cleaned data if needed
            except Exception as e:
                 st.error(f"Failed to save assignment data: {e}")
        else:
            st.warning("Please fix the errors or review warnings listed above before saving.")


# --- Bilingual Texts ---
# (Keep texts dictionary as is)
texts = {
    "English": {
        "page_title": "PLE Youth Enrollment",
        "language_label": "Choose Language",
        "teacher_search_label": "Search for a teacher by name:",
        "teacher_not_found_error": "No teacher found with that search term.",
        "enter_teacher_info": "Displaying all available teachers. Use the search box above to filter.",
        "teaches": "Teaches",
        "to_grade": "grade", # Changed slightly for better flow
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
        "name_required": "Please enter your name to register.",
        "no_teachers_available": "No teachers are currently available for enrollment." # New text
    },
    "中文": {
        "page_title": "PLE Youth 教师搜索与注册",
        "language_label": "选择语言",
        "teacher_search_label": "请输入教师姓名搜索：",
        "teacher_not_found_error": "没有匹配的教师。",
        "enter_teacher_info": "正在显示所有可用教师。使用上方搜索框筛选。",
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
        "name_required": "请输入你的名字以注册。",
        "no_teachers_available": "目前没有可报名的教师。" # New text
    }
}

# --- (Optional) CSS for Layout ---
# (Keep CSS as is)
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

# --- Main Application Logic ---

# --- Retrieve Query Param "id" and Process with Encryption ---
# Use st.query_params directly
params = st.query_params
plain_id = params.get("id", "")

# Handle potential list value from query params
if isinstance(plain_id, list):
    plain_id = plain_id[0] if plain_id else ""

if not plain_id:
    st.error("No user id provided in URL. Please use ?id=your_id or ?id=admin")
    st.stop()

# --- Routing ---
if plain_id.lower() == "admin": # Make admin check case-insensitive
    admin_route()
else:
    # --- Regular User Flow ---
    # Convert the provided id into a secure token using encryption.
    secure_id = plain_id

    # --- Sidebar Language Selector ---
    selected_language = st.sidebar.selectbox("Language / 语言", options=["English", "中文"], key="lang_select")
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
        new_user_name = st.text_input("Student's English Full Name / 学生英文全名", key="register_input") # More specific label
        if st.button(lang["register_button"], key="register_btn"):
            if new_user_name and new_user_name.strip():
                clean_name = new_user_name.strip()
                # Optional: Check if name already exists? Depends on requirements.
                # For now, allow duplicate names but unique secure_ids.
                user_database[secure_id] = clean_name
                save_data(USER_DB_PATH, user_database)
                st.success(f"Registration successful for {clean_name}! The page will now reload.")
                st.balloons()
                # Rerun to proceed to logged-in state
                st.rerun()
            else:
                st.error(lang["name_required"])
        st.stop() # Stop execution until registered

    # User is registered: get the registered user name.
    user_name = user_database.get(secure_id, "Unknown User") # Use .get for safety
    st.sidebar.write(lang["logged_in"].format(name=user_name))

    # --- Main Application: Teacher Search and Enrollment ---
    st.title(lang["page_title"])

    # Teacher filter input.
    teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter")

    # Filter the teachers (case-insensitive) from the loaded database
    # Use teachers_database instead of the hardcoded dict
    filtered_teachers = {
        name: info for name, info in teachers_database.items()
        if not teacher_filter or teacher_filter.lower() in name.lower() # Empty filter shows all
    }

    if not teachers_database:
         st.warning(lang["no_teachers_available"])
    elif not filtered_teachers:
        st.error(lang["teacher_not_found_error"])
    else:
        if not teacher_filter.strip(): # Show info only if no filter is active
             st.info(lang["enter_teacher_info"])

        # Display filtered teachers
        for teacher_name, teacher_info in filtered_teachers.items():
            st.subheader(teacher_name) # Use subheader for better structure

            # Initialize enrollment list for teacher if necessary (safety check)
            if teacher_name not in enrollments:
                enrollments[teacher_name] = []
                # No need to save here, save happens on enrollment/cancellation

            # Display teacher description.
            subject = teacher_info.get(f"subject_{selected_language.lower()[:2]}", "N/A") # e.g., subject_en or subject_zh
            grade = teacher_info.get("grade", "N/A")
            description = f"{lang['teaches']} **{subject}** ({lang['to_grade']} **{grade}**)"
            st.write(description)

            # Enrollment actions: Use two columns for buttons.
            col1, col2 = st.columns(2)

            is_enrolled = user_name in enrollments.get(teacher_name, [])

            with col1:
                # Disable enroll button if already enrolled
                enroll_clicked = st.button(
                    lang["enroll_button"],
                    key=f"enroll_button_{teacher_name}",
                    disabled=is_enrolled,
                    use_container_width=True
                )
            with col2:
                 # Disable cancel button if not enrolled
                 cancel_clicked = st.button(
                     lang["cancel_button"],
                     key=f"cancel_button_{teacher_name}",
                     disabled=not is_enrolled,
                     use_container_width=True
                 )

            if enroll_clicked:
                if not is_enrolled: # Double check state
                    if teacher_name not in enrollments: # Ensure list exists
                         enrollments[teacher_name] = []
                    enrollments[teacher_name].append(user_name)
                    save_data(ENROLLMENTS_DB_PATH, enrollments)
                    st.success(lang["enroll_success"].format(name=user_name, teacher=teacher_name))
                    st.rerun() # Rerun to update button states
                else:
                    st.info("Already enrolled.") # Should not happen if button is disabled

            # Process cancellation.
            if cancel_clicked:
                if is_enrolled: # Double check state
                    try:
                        enrollments[teacher_name].remove(user_name)
                        # Clean up empty teacher entries in enrollments if list becomes empty
                        if not enrollments[teacher_name]:
                             del enrollments[teacher_name]
                        save_data(ENROLLMENTS_DB_PATH, enrollments)
                        st.info(lang["enrollment_cancelled"])
                        st.rerun() # Rerun to update button states
                    except ValueError:
                         st.error("Could not find enrollment to cancel. Please refresh.") # Should not happen
                else:
                    st.error(lang["not_enrolled"]) # Should not happen if button is disabled

            # Display enrolled students using an expander.
            with st.expander(f"{lang['enrolled_label']} ({len(enrollments.get(teacher_name, []))})"):
                current_enrollments = enrollments.get(teacher_name, [])
                if current_enrollments:
                    # Display as a numbered list
                    for i, student_name in enumerate(current_enrollments, 1):
                         # Highlight current user's name
                         if student_name == user_name:
                             st.markdown(f"{i}. **{student_name} (You)**")
                         else:
                             st.markdown(f"{i}. {student_name}")
                else:
                    st.write(lang["no_enrollments"])
            st.markdown("---") # Separator between teachers
