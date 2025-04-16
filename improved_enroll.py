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
TEACHERS_DB_PATH = "teachers.json"

def load_data(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
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
teachers_database = load_data(TEACHERS_DB_PATH)

# --- Encryption (Deterministic) via HMAC-SHA256 ---
if "secret_key" not in st.secrets:
    st.error("`secret_key` not found in Streamlit secrets. Please add it to `.streamlit/secrets.toml`")
    st.stop()
SECRET_KEY = st.secrets["secret_key"]

def encrypt_id(plain_id: str) -> str:
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
        user_database = load_data(USER_DB_PATH)
        enrollments = load_data(ENROLLMENTS_DB_PATH)
        teachers_database = load_data(TEACHERS_DB_PATH)
        st.rerun()

    st.markdown("---")

    # --- Manage Teachers ---
    st.subheader("Manage Teachers")
    st.markdown("Add, edit, or remove teachers. Use the trash icon to remove. 'Teacher Name' must be unique.")

    teachers_list = []
    for name, details in teachers_database.items():
        teachers_list.append({
            "Teacher Name": name,
            "Subject (English)": details.get("subject_en", ""),
            "Subject (Chinese)": details.get("subject_zh", ""),
            "Grade": details.get("grade", "")
        })

    if not teachers_list:
        teachers_df = pd.DataFrame(columns=["Teacher Name", "Subject (English)", "Subject (Chinese)", "Grade"])
    else:
        teachers_df = pd.DataFrame(teachers_list)

    edited_teachers_df = st.data_editor(
        teachers_df,
        num_rows="dynamic",
        key="teacher_editor",
        column_config={
             "Teacher Name": st.column_config.TextColumn("Teacher Name", required=True),
             "Subject (English)": st.column_config.TextColumn("Subject (English)"),
             "Subject (Chinese)": st.column_config.TextColumn("Subject (Chinese)"),
             "Grade": st.column_config.TextColumn("Grade"),
        },
        use_container_width=True
    )

    if st.button("Save Changes to Teachers"):
        new_teachers_database = {}
        error_occurred = False
        seen_names = set()
        removed_teachers = set(teachers_database.keys()) - set(edited_teachers_df["Teacher Name"].dropna()) # Teachers that were deleted

        for index, row in edited_teachers_df.iterrows():
            name = row["Teacher Name"]
            if pd.isna(name) or str(name).strip() == "":
                st.error(f"Row {index+1}: Teacher Name cannot be empty.")
                error_occurred = True
                continue
            name = str(name).strip()
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
                teachers_database = new_teachers_database
                st.success("Teacher data updated successfully!")

                # Also remove enrollments associated with deleted teachers
                enrollments_updated = False
                current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh copy
                new_enrollments_after_teacher_delete = current_enrollments.copy()
                for removed_teacher in removed_teachers:
                    if removed_teacher in new_enrollments_after_teacher_delete:
                        del new_enrollments_after_teacher_delete[removed_teacher]
                        enrollments_updated = True
                        st.warning(f"Removed enrollments for deleted teacher: {removed_teacher}")

                if enrollments_updated:
                     save_data(ENROLLMENTS_DB_PATH, new_enrollments_after_teacher_delete)
                     enrollments = new_enrollments_after_teacher_delete # Update global

                st.rerun() # Refresh to show changes and potentially updated assignments
            except Exception as e:
                 st.error(f"Failed to save teacher data: {e}")
        else:
            st.warning("Please fix the errors listed above before saving teacher changes.")


    st.markdown("---")

    # --- Manage Registered Students (Edit Names / Remove) ---
    st.subheader("Manage Registered Students")
    st.markdown("Edit student names or remove students. Use the trash icon to mark for removal. Click 'Save Changes' below to confirm.")

    students_list = []
    for user_id, name in user_database.items():
         students_list.append({"Encrypted ID": user_id, "Name": name})

    if not students_list:
        students_df = pd.DataFrame(columns=["Encrypted ID", "Name"])
    else:
        students_df = pd.DataFrame(students_list)

    # Use data_editor to allow editing names and deleting rows
    edited_students_df = st.data_editor(
        students_df,
        num_rows="dynamic", # Allows deletion
        key="student_editor",
        column_config={
            "Encrypted ID": st.column_config.TextColumn("Encrypted ID (Read Only)", disabled=True), # Make ID read-only
            "Name": st.column_config.TextColumn("Student Name", required=True) # Allow editing name
        },
        use_container_width=True,
        # disabled=["Encrypted ID"] # Alternative way to disable column
    )

    if st.button("Save Changes to Students"):
        # Identify deleted students
        original_ids = set(students_df["Encrypted ID"])
        edited_ids = set(edited_students_df["Encrypted ID"])
        deleted_ids = original_ids - edited_ids
        deleted_student_names = {user_database[id] for id in deleted_ids if id in user_database} # Get names before deleting from user_db

        # Prepare the updated user database
        new_user_database = {}
        error_occurred = False
        for index, row in edited_students_df.iterrows():
            user_id = row["Encrypted ID"]
            name = row["Name"]
            if pd.isna(name) or str(name).strip() == "":
                st.error(f"Row {index+1} (ID: ...{user_id[-6:]}): Student Name cannot be empty.")
                error_occurred = True
                continue
            if pd.isna(user_id): # Should not happen if ID is disabled, but safety check
                 st.error(f"Row {index+1}: Encrypted ID is missing.")
                 error_occurred = True
                 continue
            new_user_database[user_id] = str(name).strip()

        if not error_occurred:
            try:
                # Save the updated user database
                save_data(USER_DB_PATH, new_user_database)
                user_database = new_user_database # Update global user_db
                st.success("Student data updated successfully!")
                if deleted_student_names:
                     st.info(f"Removed students: {', '.join(deleted_student_names)}")

                # Clean up enrollments for deleted students
                enrollments_updated = False
                current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh copy
                new_enrollments_after_delete = {}
                for teacher, enrolled_students in current_enrollments.items():
                    # Filter out names of students who were deleted
                    cleaned_student_list = [
                        s_name for s_name in enrolled_students
                        if s_name not in deleted_student_names
                        ]
                    if cleaned_student_list: # Only keep teacher entry if they still have students
                         new_enrollments_after_delete[teacher] = cleaned_student_list
                    # Check if the list actually changed
                    if len(cleaned_student_list) != len(enrolled_students):
                        enrollments_updated = True

                # Save cleaned enrollments if changes occurred
                if enrollments_updated:
                    save_data(ENROLLMENTS_DB_PATH, new_enrollments_after_delete)
                    enrollments = new_enrollments_after_delete # Update global enrollments
                    st.info("Removed deleted students from enrollment lists.")

                st.rerun() # Rerun to reflect changes in all admin sections

            except Exception as e:
                st.error(f"Failed to save student data or update enrollments: {e}")
        else:
             st.warning("Please fix the errors listed above before saving student changes.")


    st.markdown("---")

    # --- View and edit teacher-student assignments ---
    st.subheader("Teacher-Student Assignments")
    st.markdown("Manually assign or unassign students from teachers. Ensure names match registered students and existing teachers.")

    assignments = []
    # Use the latest in-memory 'enrollments' potentially cleaned by student/teacher deletion
    for teacher, students in enrollments.items():
        for student in students:
            assignments.append({"Teacher": teacher, "Student": student})

    if not assignments:
        assignments_df = pd.DataFrame(columns=["Teacher", "Student"])
    else:
         assignments_df = pd.DataFrame(assignments)

    # Get lists for potential dropdowns/validation
    available_teachers = list(teachers_database.keys())
    available_students = list(user_database.values()) # Names of currently registered students

    edited_assignments = st.data_editor(
        assignments_df,
        num_rows="dynamic",
        key="assignment_editor",
        column_config={
            # Using Selectbox can prevent typos but might be slow with many entries
            "Teacher": st.column_config.SelectboxColumn(
                "Teacher",
                options=available_teachers,
                required=True
            ),
            "Student": st.column_config.SelectboxColumn(
                "Student",
                options=available_students,
                required=True
            )
            # Fallback to TextColumn if Selectbox is too slow or impractical
            # "Teacher": st.column_config.TextColumn("Teacher", required=True),
            # "Student": st.column_config.TextColumn("Student", required=True),
        },
        use_container_width=True
        )

    if st.button("Save Changes to Assignments"):
        new_enrollments = {}
        error_occurred = False
        processed_pairs = set() # To detect duplicate assignments in the editor

        for index, row in edited_assignments.iterrows():
            teacher = row["Teacher"]
            student = row["Student"]

            # Basic validation
            if pd.isna(teacher) or str(teacher).strip() == "":
                 st.error(f"Row {index+1}: Teacher cannot be empty.")
                 error_occurred = True
                 continue
            if pd.isna(student) or str(student).strip() == "":
                 st.error(f"Row {index+1}: Student cannot be empty.")
                 error_occurred = True
                 continue

            teacher = str(teacher).strip()
            student = str(student).strip()

            # Check for duplicates within the edited data
            if (teacher, student) in processed_pairs:
                st.warning(f"Row {index+1}: Duplicate assignment for {student} to {teacher}. Skipping.")
                continue
            processed_pairs.add((teacher, student))

            # Validation against current databases (using the selectbox options implicitly validates)
            # if teacher not in teachers_database: # Less critical if using Selectbox
            #     st.warning(f"Row {index+1}: Teacher '{teacher}' may no longer exist.")
            # if student not in user_database.values(): # Less critical if using Selectbox
            #      st.warning(f"Row {index+1}: Student '{student}' may no longer be registered.")

            # Add to structure
            if teacher not in new_enrollments:
                new_enrollments[teacher] = []
            # Avoid double adding the same student within this save operation
            if student not in new_enrollments[teacher]:
                new_enrollments[teacher].append(student)

        if not error_occurred:
            try:
                save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                enrollments = new_enrollments # Update in-memory
                st.success("Assignments updated successfully!")
                st.rerun() # Refresh page to show cleaned data
            except Exception as e:
                 st.error(f"Failed to save assignment data: {e}")
        else:
            st.warning("Please fix the errors or review warnings listed above before saving assignments.")


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
        "to_grade": "grade",
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
        "no_teachers_available": "No teachers are currently available for enrollment."
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
        "no_teachers_available": "目前没有可报名的教师。"
    }
}

# --- (Optional) CSS --- (Keep as is)
st.markdown(
    """
    <style>
    .centered { display: flex; align-items: center; height: 100%; }
    /* Optional: Slightly larger font for admin data editors */
    /* .stDataFrame, .stDataEditor { font-size: 1.1em; } */
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Main Application Logic ---

# --- Retrieve Query Param "id" and Process with Encryption ---
params = st.query_params
plain_id = params.get("id", "")
if isinstance(plain_id, list):
    plain_id = plain_id[0] if plain_id else ""

if not plain_id:
    st.error("No user id provided in URL. Please use ?id=your_id or ?id=admin")
    st.stop()

# --- Routing ---
if plain_id.lower() == "admin":
    admin_route()
else:
    # --- Regular User Flow ---
    secure_id = encrypt_id(plain_id)
    selected_language = st.sidebar.selectbox("Language / 语言", options=["English", "中文"], key="lang_select")
    lang = texts[selected_language]

    st.markdown(f"""
        <script>document.title = "{lang['page_title']}";</script>
        """, unsafe_allow_html=True)

    # --- Registration Check ---
    if secure_id not in user_database:
        st.title(lang["page_title"])
        st.write(lang["register_prompt"])
        new_user_name = st.text_input("Student's English Full Name / 学生英文全名", key="register_input")
        if st.button(lang["register_button"], key="register_btn"):
            if new_user_name and new_user_name.strip():
                clean_name = new_user_name.strip()
                user_database[secure_id] = clean_name
                save_data(USER_DB_PATH, user_database)
                st.success(f"Registration successful for {clean_name}! The page will now reload.")
                st.balloons()
                st.rerun()
            else:
                st.error(lang["name_required"])
        st.stop()

    # --- User Logged In ---
    user_name = user_database.get(secure_id, "Unknown User")
    st.sidebar.write(lang["logged_in"].format(name=user_name))
    st.title(lang["page_title"])

    # --- Teacher Search and Enrollment ---
    teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter")

    # Use the latest teachers_database
    filtered_teachers = {
        name: info for name, info in teachers_database.items()
        if not teacher_filter or teacher_filter.lower() in name.lower()
    }

    if not teachers_database:
         st.warning(lang["no_teachers_available"])
    elif not filtered_teachers:
        st.error(lang["teacher_not_found_error"])
    else:
        if not teacher_filter.strip():
             st.info(lang["enter_teacher_info"])

        for teacher_name, teacher_info in filtered_teachers.items():
            st.subheader(teacher_name)

            subject = teacher_info.get(f"subject_{selected_language.lower()[:2]}", "N/A")
            grade = teacher_info.get("grade", "N/A")
            description = f"{lang['teaches']} **{subject}** ({lang['to_grade']} **{grade}**)"
            st.write(description)

            col1, col2 = st.columns(2)
            # Use latest 'enrollments'
            current_teacher_enrollments = enrollments.get(teacher_name, [])
            is_enrolled = user_name in current_teacher_enrollments

            with col1:
                enroll_clicked = st.button(
                    lang["enroll_button"], key=f"enroll_button_{teacher_name}",
                    disabled=is_enrolled, use_container_width=True
                )
            with col2:
                 cancel_clicked = st.button(
                     lang["cancel_button"], key=f"cancel_button_{teacher_name}",
                     disabled=not is_enrolled, use_container_width=True
                 )

            if enroll_clicked:
                if not is_enrolled:
                    if teacher_name not in enrollments: enrollments[teacher_name] = []
                    enrollments[teacher_name].append(user_name)
                    save_data(ENROLLMENTS_DB_PATH, enrollments)
                    st.success(lang["enroll_success"].format(name=user_name, teacher=teacher_name))
                    st.rerun()

            if cancel_clicked:
                if is_enrolled:
                    try:
                        enrollments[teacher_name].remove(user_name)
                        if not enrollments[teacher_name]: del enrollments[teacher_name]
                        save_data(ENROLLMENTS_DB_PATH, enrollments)
                        st.info(lang["enrollment_cancelled"])
                        st.rerun()
                    except ValueError: st.error("Enrollment inconsistency. Please refresh.")
                else: st.error(lang["not_enrolled"]) # Should be unreachable

            with st.expander(f"{lang['enrolled_label']} ({len(current_teacher_enrollments)})"):
                if current_teacher_enrollments:
                    for i, student_name in enumerate(current_teacher_enrollments, 1):
                         display_name = f"{i}. {student_name}"
                         if student_name == user_name: display_name += " **(You)**"
                         st.markdown(display_name)
                else:
                    st.write(lang["no_enrollments"])
            st.markdown("---")
