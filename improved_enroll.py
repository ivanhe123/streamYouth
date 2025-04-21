# Required library: pip install googletrans==4.0.0-rc1 streamlit pandas
# Add googletrans==4.0.0-rc1 and pandas to your requirements.txt

import streamlit as st
import json
import os
import hmac
import hashlib
import pandas as pd
import uuid
import time
from googletrans import Translator, LANGUAGES # Using googletrans (unofficial)

# --- Configuration ---
st.set_page_config(layout="wide") # Use wide layout for admin editors
st.markdown("""<style>.st-emotion-cache-1p1m4ay{ visibility:hidden }</style>""", unsafe_allow_html=True)
USER_DB_PATH = "user_db.json"
ENROLLMENTS_DB_PATH = "enrollments.json"
TEACHERS_DB_PATH = "teachers.json"

# --- RESTORED Bilingual Texts Dictionary (for UI elements) ---
texts = {
    "English": {
        "page_title": "PLE Youth Enrollment", "language_label": "Choose Language", "teacher_search_label": "Search for a teacher by name:",
        "teacher_not_found_error": "No active teacher found with that search term.", "enter_teacher_info": "Displaying all available teachers. Use the search box above to filter.",
        "teaches": "Teaches", "to_grade": "grade", "enroll_button": "Enroll", "cancel_button": "Cancel Enrollment",
        "enroll_success": "Thank you, {name}! You are now enrolled in {teacher}'s class!", "enrollment_cancelled": "Enrollment has been cancelled.",
        "register_prompt": "Welcome! Please register by entering the student's details below:", "register_button": "Register",
        "logged_in": "Logged in as: {name}", "enrolled_label": "Enrolled Students", "no_enrollments": "No students enrolled yet.",
        "not_enrolled": "Your name was not found in the enrollment.", "name_required": "Please enter your name to register.",
        "no_teachers_available": "No teachers are currently available for enrollment.", "enrollment_full": "Enrollment Full",
        "user_enrollment_caption": "Enrolled: {count} / {cap}", "unlimited": "Unlimited", "grade_select_label": "Select Grade",
        "all_grades": "All", "refresh": "Refresh", "register_name_label": "Student's English Full Name", "register_grade_label": "Current Grade",
        "register_raz_label": "RAZ Level", # <-- Added RAZ Label
        "register_country_label": "Country", "register_state_label": "State/Province", "register_city_label": "City",
        "select_country": "--- Select Country ---", "select_state": "--- Select State/Province ---", "select_city": "--- Select City ---",
        "fill_all_fields": "Please fill in Name and select a valid Country, State/Province, and City.", # RAZ not mandatory here, adjust if needed
        "already_enrolled_warning": "Already enrolled.", "registered_success": "Registered {name}! Reloading page.", "you_marker": "You",
        "save_settings_button": "Save Settings", "settings_updated_success": "Settings updated successfully!", "class_info_header": "Class Information",
        "subject_en_label": "Subject (English)", "grade_label": "Grade", "enrollment_limit_header": "Enrollment Limit",
        "max_students_label": "Maximum Students (0=unlimited)", "class_status_header": "Class Status",
        "status_active": "Active (Students can enroll)", "status_cancelled": "Cancelled (Students cannot enroll)",
        "cancel_class_button": "Cancel Class (Hide)", "reactivate_class_button": "Reactivate Class (Allow Enrollment)",
        "enrollment_overview_header": "Enrollment Overview", "current_enrollment_metric": "Current Enrollment", "enrolled_students_list_header": "Enrolled Students:",
        "teacher_dashboard_title": "Teacher Dashboard: {name}", "teacher_logout_button": "Logout", "teacher_login_title": "Teacher Portal Login",
        "teacher_id_prompt": "Enter your Teacher ID:", "login_button": "Login", "invalid_teacher_id_error": "Invalid Teacher ID.",
        "admin_dashboard_title": "Admin Dashboard", "admin_password_prompt": "Enter Admin Password:", "admin_access_granted": "Access granted.",
        "refresh_data_button": "Refresh Data from Files", "manage_teachers_header": "Manage Teachers",
        "manage_teachers_info": "Add/edit details. Set cap=0 for unlimited. Use trash icon to remove.", "save_teachers_button": "Save Changes to Teachers",
        "manage_students_header": "Manage Registered Students", "save_students_button": "Save Changes to Students",
        "manage_assignments_header": "Teacher-Student Assignments", "save_assignments_button": "Save Changes to Assignments",
        "assignment_student_details_header": "Student Details (Read-Only)", # For assignments editor
        "raz_level_column": "RAZ Level", # For admin editors
        "location_column": "Location", # For admin assignments editor
    },
    "中文": {
        "page_title": "PLE Youth 教师搜索与注册", "language_label": "选择语言", "teacher_search_label": "请输入教师姓名搜索：",
        "teacher_not_found_error": "没有匹配的可用教师。", "enter_teacher_info": "正在显示所有可用教师。使用上方搜索框筛选。",
        "teaches": "授课", "to_grade": "年级", "enroll_button": "报名", "cancel_button": "取消报名",
        "enroll_success": "谢谢, {name}! 你已注册到 {teacher} 的课程！", "enrollment_cancelled": "报名已取消。",
        "register_prompt": "欢迎！请通过输入学生的详细信息完成注册：", "register_button": "注册",
        "logged_in": "已登录: {name}", "enrolled_label": "已报名的学生", "no_enrollments": "当前没有报名的学生。",
        "not_enrolled": "未找到你的报名记录。", "name_required": "请输入你的名字以注册。",
        "no_teachers_available": "目前没有可报名的教师。", "enrollment_full": "报名已满",
        "user_enrollment_caption": "已报名: {count} / {cap}", "unlimited": "无限制", "grade_select_label": "选择年级",
        "all_grades": "所有年级", "refresh": "刷新", "register_name_label": "学生英文全名", "register_grade_label": "当前年级",
        "register_raz_label": "RAZ 等级", # <-- Added RAZ Label
        "register_country_label": "国家", "register_state_label": "州/省", "register_city_label": "城市",
        "select_country": "--- 选择国家 ---", "select_state": "--- 选择州/省 ---", "select_city": "--- 选择城市 ---",
        "fill_all_fields": "请填写姓名并选择有效的国家、州/省和城市。", # RAZ not mandatory here, adjust if needed
        "already_enrolled_warning": "已报名。", "registered_success": "已注册 {name}! 正在重新加载页面。", "you_marker": "你",
        "save_settings_button": "保存设置", "settings_updated_success": "设置已成功更新！", "class_info_header": "课程信息",
        "subject_en_label": "科目（英文）", "grade_label": "年级", "enrollment_limit_header": "报名人数限制",
        "max_students_label": "最多学生数（0表示无限制）", "class_status_header": "课程状态",
        "status_active": "开放（学生可以报名）", "status_cancelled": "已取消（学生无法报名）",
        "cancel_class_button": "取消课程（隐藏）", "reactivate_class_button": "重新激活课程（允许报名）",
        "enrollment_overview_header": "报名概览", "current_enrollment_metric": "当前报名人数", "enrolled_students_list_header": "已报名学生：",
        "teacher_dashboard_title": "教师仪表板：{name}", "teacher_logout_button": "登出", "teacher_login_title": "教师门户登录",
        "teacher_id_prompt": "输入您的教师ID：", "login_button": "登录", "invalid_teacher_id_error": "无效的教师ID。",
        "admin_dashboard_title": "管理员仪表板", "admin_password_prompt": "输入管理员密码：", "admin_access_granted": "授权成功。",
        "refresh_data_button": "从文件刷新数据", "manage_teachers_header": "管理教师",
        "manage_teachers_info": "添加/编辑详情。设置人数上限为0表示无限制。使用垃圾桶图标删除。", "save_teachers_button": "保存对教师的更改",
        "manage_students_header": "管理已注册学生", "save_students_button": "保存对学生的更改",
        "manage_assignments_header": "师生分配", "save_assignments_button": "保存分配更改",
        "assignment_student_details_header": "学生详情（只读）", # For assignments editor
        "raz_level_column": "RAZ 等级", # For admin editors
        "location_column": "位置", # For admin assignments editor
    }
}
# --- Simplified Location Data (English Only) ---
location_data = {
    "USA": { "California": ["Los Angeles", "San Francisco"], "New York": ["New York City", "Buffalo"] },
    "China": { "Beijing Municipality": ["Beijing"], "Shanghai Municipality": ["Shanghai"] },
    "Canada": { "Ontario": ["Toronto", "Ottawa"], "Quebec": ["Montreal", "Quebec City"] },
    # Add more...
}

# --- File Database Helper Functions ---
def load_data(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f: content = f.read(); return json.loads(content) if content else {}
        except (json.JSONDecodeError, IOError) as e: st.error(f"Error loading {path}: {e}"); return {}
    return {}

def save_data(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e: st.error(f"Error saving {path}: {e}")

# --- Load file databases ---
user_database_global = load_data(USER_DB_PATH)
enrollments_global = load_data(ENROLLMENTS_DB_PATH)
teachers_database_global = load_data(TEACHERS_DB_PATH)

# --- Encryption & ID Generation ---
if "secret_key" not in st.secrets: st.error("`secret_key` missing."); st.stop()
SECRET_KEY = st.secrets["secret_key"]
def encrypt_id(plain_id: str) -> str: return hmac.new(SECRET_KEY.encode(), plain_id.encode(), hashlib.sha256).hexdigest()
def generate_teacher_id(): return uuid.uuid4().hex

# --- Validate Teacher ID ---
def validate_teacher_id(entered_id: str):
    current_teachers_db = load_data(TEACHERS_DB_PATH) # Load fresh
    for name, details in current_teachers_db.items():
        if details.get("id") == entered_id: return name, details
    return None, None

# --- Teacher Dashboard (English UI) ---
def teacher_dashboard():
    # ... (Teacher dashboard code remains unchanged from previous version) ...
    global teachers_database_global, enrollments_global
    st.title(f"Teacher Dashboard: {st.session_state.teacher_name}")
    # ... (Logout, Refresh buttons) ...
    if st.button("Logout", key="teacher_logout"):
        keys_to_delete = ["teacher_logged_in", "teacher_id", "teacher_name"]
        for key in keys_to_delete:
            if key in st.session_state: del st.session_state[key]
        st.success("Logged out."); st.rerun()
    if st.button("Refresh"): st.rerun()
    st.markdown("---")
    teacher_name = st.session_state.teacher_name
    current_teachers_db = load_data(TEACHERS_DB_PATH)
    teacher_details = current_teachers_db.get(teacher_name)
    if not teacher_details: st.error("Teacher data not found."); st.stop()
    # ... (Settings Form: Subject EN, Grade, Cap) ...
    with st.form("edit_teacher_form"):
        st.write("**Class Information**")
        new_subject_en = st.text_input("Subject (English)", value=teacher_details.get("subject_en", ""))
        new_grade = st.text_input("Grade", value=teacher_details.get("grade", ""))
        st.write("**Enrollment Limit**")
        current_cap = teacher_details.get("enrollment_cap")
        cap_value = current_cap if current_cap is not None else 0
        new_cap = st.number_input("Maximum Students (0=unlimited)", min_value=0, value=cap_value, step=1, format="%d", key="teacher_edit_cap")
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            processed_cap = int(new_cap) if new_cap > 0 else None
            current_teachers_db[teacher_name].update({"subject_en": new_subject_en.strip(),"grade": new_grade.strip(),"enrollment_cap": processed_cap})
            save_data(TEACHERS_DB_PATH, current_teachers_db); teachers_database_global = current_teachers_db
            st.success("Settings updated!"); st.rerun()
    # ... (Class Status: Active/Cancel button) ...
    st.markdown("---")
    st.subheader("Class Status")
    is_active = teacher_details.get("is_active", True)
    status_text = "Active (Students can enroll)" if is_active else "Cancelled (Students cannot enroll)"
    st.success(f"Status: {status_text}") if is_active else st.warning(f"Status: {status_text}")
    btn_label = "Cancel Class (Hide)" if is_active else "Reactivate Class (Allow Enrollment)"
    btn_key = "cancel_class_btn" if is_active else "reactivate_class_btn"
    new_status = not is_active
    if st.button(btn_label, key=btn_key):
            current_teachers_db[teacher_name]["is_active"] = new_status
            save_data(TEACHERS_DB_PATH, current_teachers_db); teachers_database_global = current_teachers_db
            st.success("Class status updated."); st.rerun()
    # ... (Enrollment Overview: Metric, Student List) ...
    st.markdown("---")
    st.subheader("Enrollment Overview")
    current_enrollments = load_data(ENROLLMENTS_DB_PATH)
    enrolled_students = current_enrollments.get(teacher_name, [])
    enrollment_count = len(enrolled_students)
    display_cap = teacher_details.get("enrollment_cap")
    cap_text = "Unlimited" if display_cap is None else str(display_cap)
    st.metric("Current Enrollment", f"{enrollment_count} / {cap_text}")
    if enrolled_students:
        st.write("**Enrolled Students:**");
        for i, student_name in enumerate(sorted(enrolled_students), 1): st.markdown(f"{i}. {student_name}")
    else: st.info("No students currently enrolled.")

# --- Teacher Login Page (English UI) ---
def teacher_login_page():
    # ... (Teacher login code remains unchanged) ...
    if st.session_state.get("teacher_logged_in"): teacher_dashboard(); st.stop()
    st.title("Teacher Portal Login")
    entered_id = st.text_input("Enter your Teacher ID:", type="password", key="teacher_id_input")
    if st.button("Login", key="teacher_login_submit"):
        if not entered_id: st.warning("Please enter ID.")
        else:
            teacher_name, teacher_details = validate_teacher_id(entered_id)
            if teacher_name:
                st.session_state.teacher_logged_in = True; st.session_state.teacher_id = entered_id; st.session_state.teacher_name = teacher_name
                st.success(f"Welcome, {teacher_name}!"); st.rerun()
            else: st.error("Invalid Teacher ID.")

# --- Admin Route (Updated for RAZ level and enhanced assignments view) ---
def admin_route():
    global user_database_global, enrollments_global, teachers_database_global
    admin_lang = texts["English"] # Admin panel uses English UI text

    st.title(admin_lang["admin_dashboard_title"])
    if "passcode" not in st.secrets: st.error("Admin `passcode` missing."); st.stop()
    admin_password = st.text_input(admin_lang["admin_password_prompt"], type="password", key="admin_pw")
    if not admin_password: st.stop()
    if admin_password != st.secrets["passcode"]: st.error("Incorrect password."); st.stop()
    st.success(admin_lang["admin_access_granted"])

    if st.button(admin_lang["refresh_data_button"]):
        user_database_global = load_data(USER_DB_PATH)
        enrollments_global = load_data(ENROLLMENTS_DB_PATH)
        teachers_database_global = load_data(TEACHERS_DB_PATH)
        st.rerun()
    st.markdown("---")

    # --- Manage Teachers (Unchanged from previous version) ---
    st.subheader(admin_lang["manage_teachers_header"])
    st.markdown(admin_lang["manage_teachers_info"])
    # ... (Teacher editor code - unchanged, ensuring it handles 'subject_en' and 'enrollment_cap' correctly) ...
    # Data loading and preparation for teacher editor
    teachers_list = []
    temp_teachers_db_for_edit = load_data(TEACHERS_DB_PATH)
    needs_saving_defaults = False
    for name, details in temp_teachers_db_for_edit.items():
        if "id" not in details: details["id"] = generate_teacher_id(); needs_saving_defaults = True
        if "is_active" not in details: details["is_active"] = True; needs_saving_defaults = True
        if "enrollment_cap" not in details: details["enrollment_cap"] = None; needs_saving_defaults = True
        teachers_list.append({
            "Teacher ID": details["id"], "Teacher Name": name, "Subject (English)": details.get("subject_en", ""),
            "Grade": details.get("grade", ""), "Is Active": details.get("is_active"),
            "Enrollment Cap": details.get("enrollment_cap") if details.get("enrollment_cap") is not None else 0 })
    if needs_saving_defaults:
        save_data(TEACHERS_DB_PATH, temp_teachers_db_for_edit); teachers_database_global = temp_teachers_db_for_edit
        st.info("Applied default values to teachers. Data saved.")
    teachers_df = pd.DataFrame(teachers_list) if teachers_list else pd.DataFrame(columns=["Teacher ID", "Teacher Name", "Subject (English)", "Grade", "Is Active", "Enrollment Cap"])
    # Teacher editor UI
    edited_teachers_df = st.data_editor(
        teachers_df, num_rows="dynamic", key="teacher_editor", use_container_width=True,
        column_config={
             "Teacher ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
             "Teacher Name": st.column_config.TextColumn("Name", required=True), "Subject (English)": st.column_config.TextColumn("Subject EN"),
             "Grade": st.column_config.TextColumn("Grade", width="small"), "Is Active": st.column_config.CheckboxColumn("Active?", disabled=True, width="small"),
             "Enrollment Cap": st.column_config.NumberColumn("Cap (0=unlimited)", min_value=0, step=1, format="%d", width="small") },
        column_order=("Teacher ID", "Teacher Name", "Enrollment Cap", "Subject (English)", "Grade", "Is Active"))
    # Teacher save logic
    if st.button(admin_lang["save_teachers_button"]):
        # ... (Teacher saving logic - identical to the previous response) ...
        original_teachers_data = temp_teachers_db_for_edit; new_teachers_database = {}; error_occurred = False; seen_names = set(); processed_ids = set()
        for index, row in edited_teachers_df.iterrows():
            name = row["Teacher Name"]; teacher_id = row["Teacher ID"]; enrollment_cap_input = row["Enrollment Cap"]
            is_new_teacher = pd.isna(teacher_id) or str(teacher_id).strip() == "";
            if is_new_teacher: teacher_id = generate_teacher_id()
            if pd.isna(name) or str(name).strip() == "": st.error(f"Row {index+1}: Name empty."); error_occurred = True; continue
            name = str(name).strip()
            if name in seen_names: st.error(f"Row {index+1}: Duplicate Name '{name}'."); error_occurred = True; continue
            for existing_name, existing_details in original_teachers_data.items():
                 if existing_details.get("id") != teacher_id and existing_name == name: st.error(f"Row {index+1}: Name '{name}' conflict."); error_occurred = True; break
            if error_occurred: continue
            seen_names.add(name); processed_ids.add(teacher_id)
            processed_cap = None;
            if pd.notna(enrollment_cap_input):
                 try: cap_int = int(enrollment_cap_input); processed_cap = cap_int if cap_int > 0 else None
                 except (ValueError, TypeError): st.error(f"Row {index+1}: Invalid Cap '{enrollment_cap_input}'."); error_occurred = True; continue
            original_details = next((d for _, d in original_teachers_data.items() if d.get("id") == teacher_id), None)
            current_is_active = original_details.get("is_active", True) if original_details else True
            new_teachers_database[name] = {"id": teacher_id, "subject_en": str(row["Subject (English)"]) if pd.notna(row["Subject (English)"]) else "",
                "grade": str(row["Grade"]) if pd.notna(row["Grade"]) else "","is_active": current_is_active,"enrollment_cap": processed_cap }
        deleted_teacher_names = [n for n, d in original_teachers_data.items() if d.get("id") not in processed_ids]
        if not error_occurred:
            try:
                save_data(TEACHERS_DB_PATH, new_teachers_database); teachers_database_global = new_teachers_database
                st.success("Teacher data updated!")
                if deleted_teacher_names:
                    enrollments_updated = False; current_enrollments = load_data(ENROLLMENTS_DB_PATH); new_enrollments_after_delete = current_enrollments.copy()
                    for removed_name in deleted_teacher_names:
                        if removed_name in new_enrollments_after_delete: del new_enrollments_after_delete[removed_name]; enrollments_updated = True; st.warning(f"Removed enrollments: {removed_name}")
                    if enrollments_updated: save_data(ENROLLMENTS_DB_PATH, new_enrollments_after_delete); enrollments_global = new_enrollments_after_delete
                st.rerun()
            except Exception as e: st.error(f"Failed to save teacher data: {e}")
        else: st.warning("Fix errors before saving teacher changes.")

    st.markdown("---")

    # --- Manage Registered Students (Added RAZ Level) ---
    st.subheader(admin_lang["manage_students_header"])
    students_list = []
    temp_user_db_for_edit = load_data(USER_DB_PATH) # Load fresh for editing

    for user_id, user_info in temp_user_db_for_edit.items():
        if isinstance(user_info, dict):
            students_list.append({
                "Encrypted ID": user_id,
                "Name": user_info.get("name", ""),
                "Grade": user_info.get("grade", ""),
                "RAZ Level": user_info.get("raz_level", ""), # <-- Added RAZ Level
                "Country": user_info.get("country", ""),
                "State/Province": user_info.get("state", ""),
                "City": user_info.get("city", "")
            })
        elif isinstance(user_info, str): # Handle old format
            students_list.append({"Encrypted ID": user_id, "Name": user_info, "Grade": "", "RAZ Level": "", "Country": "", "State/Province": "", "City": ""})

    # Create DataFrame including RAZ Level
    if not students_list:
        students_df = pd.DataFrame(columns=["Encrypted ID", "Name", "Grade", "RAZ Level", "Country", "State/Province", "City"])
    else:
        students_df = pd.DataFrame(students_list)

    # Display editor with RAZ Level column
    edited_students_df = st.data_editor(
        students_df,
        num_rows="dynamic",
        key="student_editor",
        column_config={
            "Encrypted ID": st.column_config.TextColumn("Encrypted ID", disabled=True),
            "Name": st.column_config.TextColumn("Student Name", required=True),
            "Grade": st.column_config.TextColumn("Grade"),
            "RAZ Level": st.column_config.TextColumn("RAZ Level"), # <-- Added RAZ config
            "Country": st.column_config.TextColumn("Country Key"),
            "State/Province": st.column_config.TextColumn("State/Prov Key"),
            "City": st.column_config.TextColumn("City Key")
        },
        column_order=["Encrypted ID", "Name", "Grade", "RAZ Level", "Country", "State/Province", "City"], # <-- Added RAZ to order
        use_container_width=True
    )

    # Handle saving changes for students (Include RAZ Level)
    if st.button(admin_lang["save_students_button"]):
        original_ids = set(students_df["Encrypted ID"])
        edited_ids = set(edited_students_df["Encrypted ID"])
        deleted_ids = original_ids - edited_ids
        user_db_before_del = temp_user_db_for_edit
        deleted_student_names = set()
        for user_id in deleted_ids:
            info = user_db_before_del.get(user_id); deleted_student_names.add(info if isinstance(info, str) else info.get("name", "")) if info else None

        new_user_database = {}
        error_occurred = False
        name_changes = {}

        for index, row in edited_students_df.iterrows():
            user_id = row["Encrypted ID"]; name = row["Name"]
            if pd.isna(name) or str(name).strip() == "": st.error(f"Row {index+1}: Name empty."); error_occurred = True; continue
            if pd.isna(user_id): st.error(f"Row {index+1}: ID missing."); error_occurred = True; continue

            clean_name = str(name).strip()
            clean_grade = str(row["Grade"]).strip() if pd.notna(row["Grade"]) else ""
            clean_raz = str(row["RAZ Level"]).strip() if pd.notna(row["RAZ Level"]) else "" # <-- Get RAZ Level
            clean_country = str(row["Country"]).strip() if pd.notna(row["Country"]) else ""
            clean_state = str(row["State/Province"]).strip() if pd.notna(row["State/Province"]) else ""
            clean_city = str(row["City"]).strip() if pd.notna(row["City"]) else ""

            new_user_database[user_id] = { # <-- Add RAZ Level to saved data
                "name": clean_name, "grade": clean_grade, "raz_level": clean_raz,
                "country": clean_country, "state": clean_state, "city": clean_city
            }

            old_info = user_db_before_del.get(user_id)
            if old_info:
                old_name = old_info if isinstance(old_info, str) else old_info.get("name", "")
                if old_name and old_name != clean_name: name_changes[old_name] = clean_name

        if not error_occurred:
            try:
                save_data(USER_DB_PATH, new_user_database); user_database_global = new_user_database
                st.success("Student data updated!")
                valid_deleted_names = {s for s in deleted_student_names if s}
                if valid_deleted_names: st.info(f"Removed students: {', '.join(valid_deleted_names)}")

                # --- Update enrollments ---
                # ... (Enrollment update logic remains the same as previous version) ...
                enrollments_updated = False; current_enrollments = load_data(ENROLLMENTS_DB_PATH); new_enrollments = current_enrollments.copy()
                if valid_deleted_names:
                    for teacher, studs in current_enrollments.items():
                        original_length = len(studs); cleaned_list = [s for s in studs if s not in valid_deleted_names]
                        if len(cleaned_list) != original_length:
                            enrollments_updated = True; new_enrollments[teacher] = cleaned_list if cleaned_list else new_enrollments.pop(teacher, None)
                if name_changes:
                    for teacher, studs in new_enrollments.items():
                        updated_studs = [name_changes.get(s, s) for s in studs]
                        if updated_studs != studs: new_enrollments[teacher] = updated_studs; enrollments_updated = True
                if enrollments_updated: save_data(ENROLLMENTS_DB_PATH, new_enrollments); enrollments_global = new_enrollments; st.info("Updated enrollments.")
                st.rerun()
            except Exception as e: st.error(f"Failed to save student data: {e}")
        else: st.warning("Fix errors before saving student changes.")

    st.markdown("---")

    # --- Manage Teacher-Student Assignments (Enhanced View) ---
    st.subheader(admin_lang["manage_assignments_header"])
    assignments_list_enriched = []
    current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh
    user_db_for_assignments = load_data(USER_DB_PATH) # Load fresh user data

    # Create a lookup for student details
    student_details_lookup = {
        (info.get("name") if isinstance(info, dict) else info): info
        for info in user_db_for_assignments.values()
        if (isinstance(info, dict) and info.get("name")) or isinstance(info, str)
    }

    # Build the enriched list for the DataFrame
    for teacher, students in current_enrollments.items():
        for student_name in students:
            details = student_details_lookup.get(student_name)
            if isinstance(details, dict): # Found details
                location_str = f"{details.get('city', '')}, {details.get('state', '')}, {details.get('country', '')}".strip(", ")
                assignments_list_enriched.append({
                    "Teacher": teacher,
                    "Student": student_name,
                    "Grade": details.get("grade", ""),
                    admin_lang["raz_level_column"]: details.get("raz_level", ""), # Use translated header
                    admin_lang["location_column"]: location_str if location_str != "," else "", # Use translated header
                })
            else: # Student exists in enrollment but not in user_db (or old format)
                assignments_list_enriched.append({
                    "Teacher": teacher, "Student": student_name, "Grade": "N/A",
                    admin_lang["raz_level_column"]: "N/A", admin_lang["location_column"]: "N/A"
                })

    # Create DataFrame from the enriched list
    assignments_df = pd.DataFrame(assignments_list_enriched) if assignments_list_enriched else pd.DataFrame(columns=["Teacher", "Student", "Grade", admin_lang["raz_level_column"], admin_lang["location_column"]])

    # Get available options for dropdowns
    available_teachers = sorted(list(load_data(TEACHERS_DB_PATH).keys()))
    # Use the names from the lookup we already built
    available_students = sorted(list(student_details_lookup.keys()))
    if not available_teachers: available_teachers = ["(No teachers)"]
    if not available_students: available_students = ["(No students)"]

    # Display editor with read-only student details
    edited_assignments = st.data_editor(
        assignments_df,
        num_rows="dynamic",
        key="assignment_editor_enriched",
        column_config={
            "Teacher": st.column_config.SelectboxColumn("Teacher", options=available_teachers, required=True, width="medium"),
            "Student": st.column_config.SelectboxColumn("Student", options=available_students, required=True, width="medium"),
            "Grade": st.column_config.TextColumn("Grade", disabled=True, width="small"),
            admin_lang["raz_level_column"]: st.column_config.TextColumn(admin_lang["raz_level_column"], disabled=True, width="small"),
            admin_lang["location_column"]: st.column_config.TextColumn(admin_lang["location_column"], disabled=True, width="large"),
        },
        column_order=["Teacher", "Student", "Grade", admin_lang["raz_level_column"], admin_lang["location_column"]], # Show details after student
        use_container_width=True,
        hide_index=True,
    )

    # Handle saving assignments (LOGIC DOES NOT CHANGE - only Teacher/Student are processed)
    if st.button(admin_lang["save_assignments_button"]):
        new_enrollments = {}
        error_occurred = False
        processed_pairs = set()
        # Reload options just before saving for validation
        latest_teachers = list(load_data(TEACHERS_DB_PATH).keys())
        latest_user_db = load_data(USER_DB_PATH)
        latest_students = [(u["name"] if isinstance(u, dict) else u) for u in latest_user_db.values() if (isinstance(u, dict) and u.get("name")) or isinstance(u, str)]

        # Iterate through the edited DataFrame, BUT only use Teacher/Student columns
        for index, row in edited_assignments.iterrows():
            teacher, student = row["Teacher"], row["Student"]
            # --- Validation (same as before) ---
            if pd.isna(teacher) or str(teacher).strip() == "": st.error(f"Row {index+1}: Teacher empty."); error_occurred = True; continue
            if pd.isna(student) or str(student).strip() == "": st.error(f"Row {index+1}: Student empty."); error_occurred = True; continue
            teacher, student = str(teacher).strip(), str(student).strip()
            if teacher not in latest_teachers: st.error(f"Row {index+1}: Teacher '{teacher}' invalid."); error_occurred = True; continue
            if student not in latest_students: st.error(f"Row {index+1}: Student '{student}' invalid."); error_occurred = True; continue
            if (teacher, student) in processed_pairs: st.warning(f"Row {index+1}: Duplicate assignment {student}-{teacher} ignored."); continue
            processed_pairs.add((teacher, student))

            # --- Build new enrollments (using only Teacher/Student) ---
            if teacher not in new_enrollments: new_enrollments[teacher] = []
            if student not in new_enrollments[teacher]: new_enrollments[teacher].append(student)

        # --- Save if no errors (same as before) ---
        if not error_occurred:
            try:
                for teacher in new_enrollments: new_enrollments[teacher].sort() # Sort lists
                save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                enrollments_global = new_enrollments # Update global state
                st.success("Assignments updated!")
                st.rerun()
            except Exception as e: st.error(f"Failed to save assignments: {e}")
        else: st.warning("Fix errors before saving assignments.")


# --- Main Application Logic ---
params = st.query_params
plain_id = params.get("id", ""); plain_id = plain_id[0] if isinstance(plain_id, list) else plain_id
if not plain_id: st.error("No user id provided (?id=...)"); st.stop()
request_id = plain_id.lower()

# --- Routing ---
if request_id == "admin":
    admin_route()
elif request_id == "teacher":
    teacher_login_page()
else:
    # --- STUDENT/USER PATH (Added RAZ Level to Registration) ---
    selected_language = st.sidebar.selectbox(texts["English"]["language_label"] + " / " + texts["中文"]["language_label"], options=["English", "中文"], key="lang_select")
    lang = texts.get(selected_language, texts["English"])
    lang_code = 'en' if selected_language == 'English' else 'zh-cn'
    secure_id = request_id
    st.markdown(f"""<script>document.title = "{lang['page_title']}";</script>""", unsafe_allow_html=True)

    def format_location(location_name): # Needs to be defined in this scope
        if selected_language == "English" or not translator: return location_name
        return translate_dynamic_text(translator, location_name, lang_code)

    user_database = load_data(USER_DB_PATH)
    teachers_database = load_data(TEACHERS_DB_PATH)
    enrollments = load_data(ENROLLMENTS_DB_PATH)

    # --- REGISTRATION Section (Added RAZ Level Input) ---
    if secure_id not in user_database:
        st.title(lang["page_title"])
        st.write(lang["register_prompt"])
        new_user_name = st.text_input(lang["register_name_label"], key="reg_name")
        new_user_grade = st.text_input(lang["register_grade_label"], key="reg_grade")
        new_user_raz = st.text_input(lang["register_raz_label"], key="reg_raz") # <-- Added RAZ Input

        # Location Dropdowns
        country_options = [lang["select_country"]] + sorted(location_data.keys())
        selected_country = st.selectbox(lang["register_country_label"], options=country_options, key="reg_country", index=0, format_func=format_location)
        state_options = [lang["select_state"]]
        if selected_country != lang["select_country"] and selected_country in location_data: state_options.extend(sorted(location_data[selected_country].keys()))
        selected_state = st.selectbox(lang["register_state_label"], options=state_options, key="reg_state", index=0, disabled=(selected_country == lang["select_country"]), format_func=format_location)
        city_options = [lang["select_city"]]
        if selected_state != lang["select_state"] and selected_country in location_data and selected_state in location_data[selected_country]: city_options.extend(sorted(location_data[selected_country][selected_state]))
        selected_city = st.selectbox(lang["register_city_label"], options=city_options, key="reg_city", index=0, disabled=(selected_state == lang["select_state"]), format_func=format_location)

        st.markdown("---")
        if st.button(lang["register_button"], key="register_btn"):
            # Basic validation (RAZ is optional here)
            if new_user_name.strip() and selected_country != lang["select_country"] and selected_state != lang["select_state"] and selected_city != lang["select_city"]:
                user_data_to_save = {
                    "name": new_user_name.strip(),
                    "grade": new_user_grade.strip(),
                    "raz_level": new_user_raz.strip(), # <-- Save RAZ Level
                    "country": selected_country, "state": selected_state, "city": selected_city
                }
                user_database[secure_id] = user_data_to_save
                save_data(USER_DB_PATH, user_database); user_database_global = user_database # Update global
                st.success(lang["registered_success"].format(name=new_user_name.strip()))
                st.balloons(); time.sleep(1); st.rerun()
            else: st.error(lang["fill_all_fields"])
        st.stop()

    # --- MAIN ENROLLMENT Section (No changes needed here for RAZ) ---
    user_info = user_database.get(secure_id)
    if isinstance(user_info, dict): user_name = user_info.get("name", "Unknown")
    elif isinstance(user_info, str): user_name = user_info
    else: user_name = "Unknown"; st.sidebar.error("User data error.")

    st.sidebar.write(lang["logged_in"].format(name=user_name))
    if isinstance(user_info, dict): # Display location/details in sidebar
        c, s, ci = user_info.get("country"), user_info.get("state"), user_info.get("city")
        gr = user_info.get("grade")
        rz = user_info.get("raz_level")
        loc_str = f"{format_location(ci)}, {format_location(s)}, {format_location(c)}" if c and s and ci else ""
        details_str = f"Grade: {gr}" if gr else ""
        if rz: details_str += f" | RAZ: {rz}"
        if loc_str: st.sidebar.caption(loc_str)
        if details_str: st.sidebar.caption(details_str)

    st.title(lang["page_title"])
    if st.sidebar.button(lang["refresh"]): st.rerun()

    # ... (Teacher Search and Filter logic remains the same) ...
    st.subheader(lang["teacher_search_label"])
    col_search, col_grade_filter = st.columns([3, 2])
    with col_search: teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter", label_visibility="collapsed")
    active_teachers = {n: i for n, i in teachers_database.items() if i.get("is_active", True)}
    unique_grades = sorted(list({str(i.get("grade","")).strip() for i in active_teachers.values() if str(i.get("grade","")).strip()}))
    grade_options = [lang["all_grades"]] + unique_grades
    with col_grade_filter: selected_grade_filter = st.selectbox(lang["grade_select_label"], options=grade_options, key="grade_select")
    filtered_teachers = {}
    if active_teachers:
        term = teacher_filter.strip().lower()
        for n, i in active_teachers.items():
            name_match = (not term) or (term in n.lower())
            grade_match = (selected_grade_filter == lang["all_grades"]) or (str(i.get("grade","")).strip() == selected_grade_filter)
            if name_match and grade_match: filtered_teachers[n] = i
    st.markdown("---")

    # ... (Display Teachers logic remains the same) ...
    if not active_teachers: st.warning(lang["no_teachers_available"])
    elif not filtered_teachers: st.error(lang["teacher_not_found_error"])
    else:
        for teacher_name, teacher_info in filtered_teachers.items():
            st.subheader(teacher_name)
            subject_en = teacher_info.get("subject_en", "N/A")
            display_subject = subject_en
            if selected_language != "English" and translator: display_subject = translate_dynamic_text(translator, subject_en, lang_code)
            grade = teacher_info.get("grade", "N/A")
            desc_parts = [];
            if display_subject != "N/A": desc_parts.append(f"**{display_subject}**")
            if grade != "N/A": desc_parts.append(f"({lang['to_grade']} **{grade}**)")
            st.write(f"{lang['teaches']} {' '.join(desc_parts)}" if desc_parts else f"({lang['teaches']} N/A)")
            current_teacher_enrollments = enrollments.get(teacher_name, [])
            count = len(current_teacher_enrollments); cap = teacher_info.get("enrollment_cap"); cap_text = lang["unlimited"] if cap is None else str(cap)
            is_full = False if cap is None else count >= cap
            st.caption(lang["user_enrollment_caption"].format(count=count, cap=cap_text))
            col1, col2 = st.columns(2); is_enrolled = user_name in current_teacher_enrollments
            with col1: enroll_label = lang["enrollment_full"] if is_full and not is_enrolled else lang["enroll_button"]; enroll_disabled = is_enrolled or is_full; enroll_clicked = st.button(enroll_label, key=f"enroll_{teacher_name}", disabled=enroll_disabled, use_container_width=True)
            with col2: cancel_clicked = st.button(lang["cancel_button"], key=f"cancel_{teacher_name}", disabled=not is_enrolled, use_container_width=True)
            if enroll_clicked:
                # ... (Enroll click logic remains the same) ...
                enrollments_now = load_data(ENROLLMENTS_DB_PATH); teacher_list_now = enrollments_now.get(teacher_name, []); teacher_info_now = load_data(TEACHERS_DB_PATH).get(teacher_name, {}); cap_now = teacher_info_now.get("enrollment_cap"); is_full_now = False if cap_now is None else len(teacher_list_now) >= cap_now
                if user_name not in teacher_list_now and not is_full_now:
                    teacher_list_now.append(user_name); enrollments_now[teacher_name] = teacher_list_now; save_data(ENROLLMENTS_DB_PATH, enrollments_now); enrollments_global = enrollments_now
                    st.success(lang["enroll_success"].format(name=user_name, teacher=teacher_name)); st.rerun()
            if cancel_clicked:
                # ... (Cancel click logic remains the same) ...
                enrollments_now = load_data(ENROLLMENTS_DB_PATH)
                if teacher_name in enrollments_now and user_name in enrollments_now[teacher_name]:
                    enrollments_now[teacher_name].remove(user_name);
                    if not enrollments_now[teacher_name]: del enrollments_now[teacher_name]
                    save_data(ENROLLMENTS_DB_PATH, enrollments_now); enrollments_global = enrollments_now
                    st.info(lang["enrollment_cancelled"]); st.rerun()
            with st.expander(f"{lang['enrolled_label']} ({count})"):
                # ... (Expander display logic remains the same) ...
                 if current_teacher_enrollments:
                    for i, name in enumerate(sorted(current_teacher_enrollments), 1): marker = f" **({lang['you_marker']})**" if name == user_name else ""; st.markdown(f"{i}. {name}{marker}")
                 else: st.write(lang["no_enrollments"])
            st.markdown("---")
