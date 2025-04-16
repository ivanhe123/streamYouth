import streamlit as st
import json
import os
import hmac
import hashlib
import pandas as pd
import uuid # Import the uuid library

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
# Use functions to load dynamically within routes if frequent updates are expected
# For simplicity here, load globally but be aware of potential staleness without refreshes.
user_database = load_data(USER_DB_PATH)
enrollments = load_data(ENROLLMENTS_DB_PATH)
teachers_database = load_data(TEACHERS_DB_PATH)

# --- Encryption (Deterministic) via HMAC-SHA256 ---
if "secret_key" not in st.secrets:
    st.error("`secret_key` not found in Streamlit secrets.")
    st.stop()
SECRET_KEY = st.secrets["secret_key"]

def encrypt_id(plain_id: str) -> str:
    return hmac.new(SECRET_KEY.encode(), plain_id.encode(), hashlib.sha256).hexdigest()

# --- Generate Teacher ID ---
def generate_teacher_id():
    return uuid.uuid4().hex

# --- Validate Teacher ID ---
def validate_teacher_id(entered_id: str):
    """Checks if a teacher ID exists and returns the teacher's name and details if valid."""
    # Reload teacher data for validation to ensure it's fresh
    current_teachers_db = load_data(TEACHERS_DB_PATH)
    for name, details in current_teachers_db.items():
        if details.get("id") == entered_id:
            return name, details
    return None, None

# --- Teacher Dashboard ---
def teacher_dashboard():
    """Displays the dashboard for the logged-in teacher."""
    global teachers_database, enrollments # Allow modification

    st.title(f"Teacher Dashboard: {st.session_state.teacher_name}")

    if st.button("Logout", key="teacher_logout"):
        # Clear teacher-specific session state
        del st.session_state.teacher_logged_in
        del st.session_state.teacher_id
        del st.session_state.teacher_name
        st.success("Logged out.")
        st.rerun() # Go back to login prompt

    st.markdown("---")

    # Get current details - reload data for freshness
    teacher_name = st.session_state.teacher_name
    current_teachers_db = load_data(TEACHERS_DB_PATH)
    teacher_details = current_teachers_db.get(teacher_name)

    if not teacher_details:
        st.error("Could not find your teacher data. Please contact admin.")
        st.stop()

    # --- Edit Class Details ---
    st.subheader("Edit Class Details")
    with st.form("edit_teacher_form"):
        new_subject_en = st.text_input(
            "Subject (English)",
            value=teacher_details.get("subject_en", ""),
            key=f"edit_subj_en_{teacher_name}" # Add unique key
        )
        new_subject_zh = st.text_input(
            "Subject (Chinese)",
            value=teacher_details.get("subject_zh", ""),
            key=f"edit_subj_zh_{teacher_name}"
        )
        new_grade = st.text_input(
            "Grade",
            value=teacher_details.get("grade", ""),
            key=f"edit_grade_{teacher_name}"
        )
        submitted = st.form_submit_button("Save Details")
        if submitted:
            # Update the details in the loaded database dictionary
            current_teachers_db[teacher_name]["subject_en"] = new_subject_en.strip()
            current_teachers_db[teacher_name]["subject_zh"] = new_subject_zh.strip()
            current_teachers_db[teacher_name]["grade"] = new_grade.strip()
            # Save the entire updated database
            save_data(TEACHERS_DB_PATH, current_teachers_db)
            teachers_database = current_teachers_db # Update global state
            st.success("Class details updated successfully!")
            # No rerun needed unless you want to clear the form state implicitly

    st.markdown("---")

    # --- Class Status (Active/Cancelled) ---
    st.subheader("Class Status")
    is_active = teacher_details.get("is_active", True) # Default to active if key doesn't exist

    if is_active:
        st.success("Status: Active (Students can enroll)")
        if st.button("Cancel Class (Hide from Enrollment)", key="cancel_class_btn"):
            current_teachers_db[teacher_name]["is_active"] = False
            save_data(TEACHERS_DB_PATH, current_teachers_db)
            teachers_database = current_teachers_db # Update global state
            st.warning("Class cancelled. Students can no longer enroll.")
            st.rerun() # Rerun to update status display and button
    else:
        st.warning("Status: Cancelled (Students cannot enroll)")
        if st.button("Reactivate Class (Allow Enrollment)", key="reactivate_class_btn"):
            current_teachers_db[teacher_name]["is_active"] = True
            save_data(TEACHERS_DB_PATH, current_teachers_db)
            teachers_database = current_teachers_db # Update global state
            st.success("Class reactivated. Students can now enroll.")
            st.rerun() # Rerun to update status display and button

    st.markdown("---")

    # --- View Enrolled Students ---
    st.subheader("Enrolled Students")
    current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh enrollment data
    enrolled_students = current_enrollments.get(teacher_name, [])

    if enrolled_students:
        st.write(f"You have {len(enrolled_students)} student(s) enrolled:")
        # Display as a list
        for i, student_name in enumerate(enrolled_students, 1):
             st.markdown(f"{i}. {student_name}")
    else:
        st.info("No students are currently enrolled in your class.")


# --- Teacher Login Page ---
def teacher_login_page():
    """Handles the teacher ID input and validation."""

    # If already logged in, show dashboard directly
    if st.session_state.get("teacher_logged_in"):
        teacher_dashboard()
        st.stop() # Stop execution here

    st.title("Teacher Portal Login")
    entered_id = st.text_input("Enter your Teacher ID:", type="password", key="teacher_id_input")

    if st.button("Login", key="teacher_login_submit"):
        if not entered_id:
            st.warning("Please enter your Teacher ID.")
        else:
            teacher_name, teacher_details = validate_teacher_id(entered_id)
            if teacher_name and teacher_details:
                st.session_state.teacher_logged_in = True
                st.session_state.teacher_id = entered_id
                st.session_state.teacher_name = teacher_name # Store name for easy access
                st.success(f"Welcome, {teacher_name}!")
                st.rerun() # Rerun to load the dashboard
            else:
                st.error("Invalid Teacher ID. Please try again or contact an admin.")

# --- Admin Route ---
def admin_route():
    global user_database, enrollments, teachers_database

    st.title("Admin Dashboard")
    if "passcode" not in st.secrets:
        st.error("Admin `passcode` not found in Streamlit secrets.")
        st.stop()
    admin_password = st.text_input("Enter Admin Password:", type="password", key="admin_pw")
    if not admin_password: st.warning("Please enter the admin password."); st.stop()
    if admin_password != st.secrets["passcode"]: st.error("Incorrect password."); st.stop()
    st.success("Access granted. Welcome, Admin!")

    if st.button("Refresh Data from Files"):
        user_database = load_data(USER_DB_PATH)
        enrollments = load_data(ENROLLMENTS_DB_PATH)
        teachers_database = load_data(TEACHERS_DB_PATH)
        st.rerun()
    st.markdown("---")

    # --- Manage Teachers ---
    st.subheader("Manage Teachers")
    st.markdown("Add/edit teacher details. 'Teacher ID' is auto-generated. 'Teacher Name' must be unique. Use trash icon to remove.")

    teachers_list = []
    needs_saving_for_ids_or_status = False
    temp_teachers_db = load_data(TEACHERS_DB_PATH) # Load fresh for processing

    for name, details in temp_teachers_db.items():
        teacher_id = details.get("id")
        if not teacher_id:
            teacher_id = generate_teacher_id()
            details["id"] = teacher_id
            needs_saving_for_ids_or_status = True
        # Ensure 'is_active' exists, default to True
        if "is_active" not in details:
             details["is_active"] = True
             needs_saving_for_ids_or_status = True

        teachers_list.append({
            "Teacher ID": teacher_id,
            "Teacher Name": name,
            "Subject (English)": details.get("subject_en", ""),
            "Subject (Chinese)": details.get("subject_zh", ""),
            "Grade": details.get("grade", ""),
            "Is Active": details.get("is_active", True) # Add status column
        })

    if needs_saving_for_ids_or_status:
        save_data(TEACHERS_DB_PATH, temp_teachers_db)
        teachers_database = temp_teachers_db # Update global
        st.info("Generated missing Teacher IDs and/or Status flags. Data saved.")

    if not teachers_list:
        teachers_df = pd.DataFrame(columns=["Teacher ID", "Teacher Name", "Subject (English)", "Subject (Chinese)", "Grade", "Is Active"])
    else:
        teachers_df = pd.DataFrame(teachers_list)

    edited_teachers_df = st.data_editor(
        teachers_df,
        num_rows="dynamic",
        key="teacher_editor",
        column_config={
             "Teacher ID": st.column_config.TextColumn("Teacher ID", disabled=True),
             "Teacher Name": st.column_config.TextColumn("Teacher Name", required=True),
             "Subject (English)": st.column_config.TextColumn("Subject (English)"),
             "Subject (Chinese)": st.column_config.TextColumn("Subject (Chinese)"),
             "Grade": st.column_config.TextColumn("Grade"),
             "Is Active": st.column_config.CheckboxColumn("Is Active?", disabled=True) # Show status, disable editing here
        },
        column_order=("Teacher ID", "Teacher Name", "Subject (English)", "Subject (Chinese)", "Grade", "Is Active"),
        use_container_width=True
    )

    if st.button("Save Changes to Teachers"):
        original_teachers_data = teachers_database.copy()
        new_teachers_database = {}
        error_occurred = False
        seen_names = set()
        processed_ids = set()

        for index, row in edited_teachers_df.iterrows():
            name = row["Teacher Name"]
            teacher_id = row["Teacher ID"]
            is_active = row["Is Active"] # Get status, even though disabled

            if pd.isna(teacher_id) or str(teacher_id).strip() == "":
                is_new_teacher = True
                teacher_id = generate_teacher_id()
            else:
                is_new_teacher = True
                for _, details in original_teachers_data.items():
                    if details.get("id") == teacher_id: is_new_teacher = False; break

            if pd.isna(name) or str(name).strip() == "":
                st.error(f"Row {index+1}: Teacher Name cannot be empty."); error_occurred = True; continue
            name = str(name).strip()
            if name in seen_names:
                 st.error(f"Row {index+1}: Duplicate Teacher Name '{name}'."); error_occurred = True; continue

            if not is_new_teacher: # Check name uniqueness against others if name changed
                 for existing_name, existing_details in original_teachers_data.items():
                     if existing_details.get("id") != teacher_id and existing_name == name:
                         st.error(f"Row {index+1}: Name '{name}' used by another teacher."); error_occurred = True; break
                 if error_occurred: continue

            seen_names.add(name)
            processed_ids.add(teacher_id)

            # Get the 'is_active' status from the *original* data if it exists,
            # otherwise default to True for new teachers or keep the value from the editor
            # (which should reflect the original if the column is disabled).
            original_details = next((d for _, d in original_teachers_data.items() if d.get("id") == teacher_id), None)
            current_is_active = original_details.get("is_active", True) if original_details else True


            new_teachers_database[name] = {
                "id": teacher_id,
                "subject_en": str(row["Subject (English)"]) if pd.notna(row["Subject (English)"]) else "",
                "subject_zh": str(row["Subject (Chinese)"]) if pd.notna(row["Subject (Chinese)"]) else "",
                "grade": str(row["Grade"]) if pd.notna(row["Grade"]) else "",
                "is_active": current_is_active # Preserve existing status, default to True for new
            }

        deleted_teacher_names = []
        for original_name, original_details in original_teachers_data.items():
            if original_details.get("id") not in processed_ids:
                deleted_teacher_names.append(original_name)

        if not error_occurred:
            try:
                save_data(TEACHERS_DB_PATH, new_teachers_database)
                teachers_database = new_teachers_database
                st.success("Teacher data updated successfully!")

                enrollments_updated = False
                current_enrollments = load_data(ENROLLMENTS_DB_PATH)
                new_enrollments_after_teacher_delete = current_enrollments.copy()
                for removed_teacher_name in deleted_teacher_names:
                    if removed_teacher_name in new_enrollments_after_teacher_delete:
                        del new_enrollments_after_teacher_delete[removed_teacher_name]
                        enrollments_updated = True
                        st.warning(f"Removed enrollments for deleted teacher: {removed_teacher_name}")

                if enrollments_updated:
                     save_data(ENROLLMENTS_DB_PATH, new_enrollments_after_teacher_delete)
                     enrollments = new_enrollments_after_teacher_delete

                st.rerun()
            except Exception as e:
                 st.error(f"Failed to save teacher data or update enrollments: {e}")
        else:
            st.warning("Please fix the errors listed above before saving teacher changes.")

    st.markdown("---")

    # --- Manage Registered Students (Keep as is) ---
    st.subheader("Manage Registered Students")
    # ... (student management code remains the same) ...
    students_list = []
    for user_id, name in user_database.items():
         students_list.append({"Encrypted ID": user_id, "Name": name})

    if not students_list: students_df = pd.DataFrame(columns=["Encrypted ID", "Name"])
    else: students_df = pd.DataFrame(students_list)

    edited_students_df = st.data_editor(
        students_df, num_rows="dynamic", key="student_editor",
        column_config={
            "Encrypted ID": st.column_config.TextColumn("Encrypted ID", disabled=True),
            "Name": st.column_config.TextColumn("Student Name", required=True) },
        use_container_width=True)

    if st.button("Save Changes to Students"):
        original_ids = set(students_df["Encrypted ID"])
        edited_ids = set(edited_students_df["Encrypted ID"])
        deleted_ids = original_ids - edited_ids
        deleted_student_names = {user_database[id] for id in deleted_ids if id in user_database}
        new_user_database = {}
        error_occurred = False
        for index, row in edited_students_df.iterrows():
            user_id, name = row["Encrypted ID"], row["Name"]
            if pd.isna(name) or str(name).strip() == "": st.error(f"Row {index+1}: Student Name empty."); error_occurred = True; continue
            if pd.isna(user_id): st.error(f"Row {index+1}: Encrypted ID missing."); error_occurred = True; continue
            new_user_database[user_id] = str(name).strip()
        if not error_occurred:
            try:
                save_data(USER_DB_PATH, new_user_database)
                user_database = new_user_database
                st.success("Student data updated!")
                if deleted_student_names: st.info(f"Removed students: {', '.join(deleted_student_names)}")
                enrollments_updated = False
                current_enrollments = load_data(ENROLLMENTS_DB_PATH)
                new_enrollments_after_delete = {}
                for teacher, studs in current_enrollments.items():
                    cleaned_list = [s for s in studs if s not in deleted_student_names]
                    if cleaned_list: new_enrollments_after_delete[teacher] = cleaned_list
                    if len(cleaned_list) != len(studs): enrollments_updated = True
                if enrollments_updated:
                    save_data(ENROLLMENTS_DB_PATH, new_enrollments_after_delete)
                    enrollments = new_enrollments_after_delete
                    st.info("Removed deleted students from enrollments.")
                st.rerun()
            except Exception as e: st.error(f"Failed to save student data: {e}")
        else: st.warning("Fix errors before saving student changes.")


    st.markdown("---")

    # --- View and edit teacher-student assignments (Keep as is) ---
    st.subheader("Teacher-Student Assignments")
    # ... (assignment management code remains the same) ...
    assignments = []
    for teacher, students in enrollments.items():
        for student in students: assignments.append({"Teacher": teacher, "Student": student})
    if not assignments: assignments_df = pd.DataFrame(columns=["Teacher", "Student"])
    else: assignments_df = pd.DataFrame(assignments)
    available_teachers = list(load_data(TEACHERS_DB_PATH).keys()) # Use fresh list
    available_students = list(load_data(USER_DB_PATH).values()) # Use fresh list
    edited_assignments = st.data_editor(
        assignments_df, num_rows="dynamic", key="assignment_editor",
        column_config={
            "Teacher": st.column_config.SelectboxColumn("Teacher", options=available_teachers, required=True),
            "Student": st.column_config.SelectboxColumn("Student", options=available_students, required=True) },
        use_container_width=True)
    if st.button("Save Changes to Assignments"):
        new_enrollments = {}
        error_occurred = False; processed_pairs = set()
        for index, row in edited_assignments.iterrows():
            teacher, student = row["Teacher"], row["Student"]
            if pd.isna(teacher) or str(teacher).strip() == "": st.error(f"Row {index+1}: Teacher empty."); error_occurred = True; continue
            if pd.isna(student) or str(student).strip() == "": st.error(f"Row {index+1}: Student empty."); error_occurred = True; continue
            teacher, student = str(teacher).strip(), str(student).strip()
            if (teacher, student) in processed_pairs: st.warning(f"Row {index+1}: Duplicate assignment {student} to {teacher}."); continue
            processed_pairs.add((teacher, student))
            if teacher not in new_enrollments: new_enrollments[teacher] = []
            if student not in new_enrollments[teacher]: new_enrollments[teacher].append(student)
        if not error_occurred:
            try:
                save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                enrollments = new_enrollments
                st.success("Assignments updated!"); st.rerun()
            except Exception as e: st.error(f"Failed to save assignments: {e}")
        else: st.warning("Fix errors before saving assignments.")


# --- Bilingual Texts --- (Keep as is)
texts = {
    "English": { "page_title": "PLE Youth Enrollment", "language_label": "Choose Language", "teacher_search_label": "Search for a teacher by name:", "teacher_not_found_error": "No active teacher found with that search term.", "enter_teacher_info": "Displaying all available teachers. Use the search box above to filter.", "teaches": "Teaches", "to_grade": "grade", "enroll_button": "Enroll", "cancel_button": "Cancel Enrollment", "enroll_success": "Thank you, {name}! You are now enrolled in {teacher}'s class!", "enrollment_cancelled": "Enrollment has been cancelled.", "register_prompt": "Welcome! Please register by entering the student's English Full name below:", "register_button": "Register", "logged_in": "Logged in as: {name}", "enrolled_label": "Enrolled Students", "no_enrollments": "No students enrolled yet.", "not_enrolled": "Your name was not found in the enrollment.", "name_required": "Please enter your name to register.", "no_teachers_available": "No teachers are currently available for enrollment." },
    "中文": { "page_title": "PLE Youth 教师搜索与注册", "language_label": "选择语言", "teacher_search_label": "请输入教师姓名搜索：", "teacher_not_found_error": "没有匹配的可用教师。", "enter_teacher_info": "正在显示所有可用教师。使用上方搜索框筛选。", "teaches": "授课", "to_grade": "年级", "enroll_button": "报名", "cancel_button": "取消报名", "enroll_success": "谢谢, {name}! 你已注册到 {teacher} 的课程！", "enrollment_cancelled": "报名已取消。", "register_prompt": "欢迎！请通过输入学生的英文（或拼音）全名完成注册：", "register_button": "注册", "logged_in": "已登录: {name}", "enrolled_label": "已报名的学生", "no_enrollments": "当前没有报名的学生。", "not_enrolled": "未找到你的报名记录。", "name_required": "请输入你的名字以注册。", "no_teachers_available": "目前没有可报名的教师。" }
}

# --- CSS --- (Keep as is)
st.markdown(""" <style> .centered { display: flex; align-items: center; height: 100%; } </style> """, unsafe_allow_html=True,)

# --- Main Application Logic ---
params = st.query_params
plain_id = params.get("id", "")
if isinstance(plain_id, list): plain_id = plain_id[0] if plain_id else ""

if not plain_id:
    st.error("No user id provided in URL. Please use ?id=your_id, ?id=admin, or ?id=teacher")
    st.stop()

# --- Routing ---
request_id = plain_id.lower() # Use lowercase for routing comparison

if request_id == "admin":
    admin_route()
elif request_id == "teacher":
    teacher_login_page() # Handles login prompt OR dashboard display
else:
    # --- Regular User Flow ---
    secure_id = encrypt_id(plain_id)
    selected_language = st.sidebar.selectbox("Language / 语言", options=["English", "中文"], key="lang_select")
    lang = texts[selected_language]
    st.markdown(f"""<script>document.title = "{lang['page_title']}";</script>""", unsafe_allow_html=True)

    # Reload data for user view
    user_database = load_data(USER_DB_PATH)
    teachers_database = load_data(TEACHERS_DB_PATH)
    enrollments = load_data(ENROLLMENTS_DB_PATH)

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
                st.balloons(); st.rerun()
            else: st.error(lang["name_required"])
        st.stop()

    # --- User Logged In ---
    user_name = user_database.get(secure_id, "Unknown User")
    st.sidebar.write(lang["logged_in"].format(name=user_name))
    st.title(lang["page_title"])

    # --- Teacher Search and Enrollment (Filter Active Teachers) ---
    teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter")

    # Filter only ACTIVE teachers from the loaded database
    active_teachers = {
        name: info for name, info in teachers_database.items()
        if info.get("is_active", True) # Check the flag, default to True if missing
    }

    filtered_teachers = {
        name: info for name, info in active_teachers.items()
        if not teacher_filter or teacher_filter.lower() in name.lower()
    }

    if not active_teachers: # Check if there are any active teachers at all
         st.warning(lang["no_teachers_available"])
    elif not filtered_teachers: # Check if filter returned results
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
            current_teacher_enrollments = enrollments.get(teacher_name, [])
            is_enrolled = user_name in current_teacher_enrollments

            with col1: enroll_clicked = st.button(lang["enroll_button"], key=f"enroll_button_{teacher_name}", disabled=is_enrolled, use_container_width=True)
            with col2: cancel_clicked = st.button(lang["cancel_button"], key=f"cancel_button_{teacher_name}", disabled=not is_enrolled, use_container_width=True)

            if enroll_clicked and not is_enrolled:
                if teacher_name not in enrollments: enrollments[teacher_name] = []
                enrollments[teacher_name].append(user_name)
                save_data(ENROLLMENTS_DB_PATH, enrollments)
                st.success(lang["enroll_success"].format(name=user_name, teacher=teacher_name)); st.rerun()

            if cancel_clicked and is_enrolled:
                try:
                    enrollments[teacher_name].remove(user_name)
                    if not enrollments[teacher_name]: del enrollments[teacher_name]
                    save_data(ENROLLMENTS_DB_PATH, enrollments)
                    st.info(lang["enrollment_cancelled"]); st.rerun()
                except ValueError: st.error("Enrollment inconsistency. Please refresh.")

            with st.expander(f"{lang['enrolled_label']} ({len(current_teacher_enrollments)})"):
                if current_teacher_enrollments:
                    for i, student_name in enumerate(current_teacher_enrollments, 1):
                        display_name = f"{i}. {student_name}" + (" **(You)**" if student_name == user_name else "")
                        st.markdown(display_name)
                else: st.write(lang["no_enrollments"])
            st.markdown("---")
