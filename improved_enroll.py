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

# --- Translation Setup (ONLY for dynamic content) ---
try:
    translator = Translator(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
except Exception as e:
    st.error(f"Translator init failed: {e}. Location translation may fail.")
    translator = None

@st.cache_data(ttl=3600)
def translate_dynamic_text(_translator, text, target_lang_code):
    if not _translator or not text or target_lang_code == 'en': return text
    if target_lang_code == 'zh': target_lang_code = 'zh-cn'
    if target_lang_code not in LANGUAGES and target_lang_code not in ['zh-cn', 'zh-tw']: return text
    try:
        translated = _translator.translate(text, dest=target_lang_code); return translated.text
    except Exception as e:
        print(f"WARN: Dyn Translate Error '{text}' to {target_lang_code}: {e}"); return text
# --- End Translation Setup ---

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
        "register_country_label": "Country", "register_state_label": "State/Province", "register_city_label": "City",
        "select_country": "--- Select Country ---", "select_state": "--- Select State/Province ---", "select_city": "--- Select City ---",
        "fill_all_fields": "Please fill in Name and select a valid Country, State/Province, and City.", "already_enrolled_warning": "Already enrolled.",
        "registered_success": "Registered {name}! Reloading page.", "you_marker": "You",
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
        "register_country_label": "国家", "register_state_label": "州/省", "register_city_label": "城市",
        "select_country": "--- 选择国家 ---", "select_state": "--- 选择州/省 ---", "select_city": "--- 选择城市 ---",
        "fill_all_fields": "请填写姓名并选择有效的国家、州/省和城市。", "already_enrolled_warning": "已报名。",
        "registered_success": "已注册 {name}! 正在重新加载页面。", "you_marker": "你",
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
# These act as the initial state. Functions should reload if fresh data is needed.
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
    current_teachers_db = load_data(TEACHERS_DB_PATH) # Load fresh data for validation
    for name, details in current_teachers_db.items():
        if details.get("id") == entered_id: return name, details
    return None, None

# --- Teacher Dashboard (Simplified - English UI) ---
def teacher_dashboard():
    global teachers_database_global, enrollments_global # Allow updates to global state
    st.title(f"Teacher Dashboard: {st.session_state.teacher_name}")
    if st.button("Logout", key="teacher_logout"):
        # Clear session state related to teacher login
        keys_to_delete = ["teacher_logged_in", "teacher_id", "teacher_name"]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        st.success("Logged out."); st.rerun()
    if st.button("Refresh"): st.rerun()
    st.markdown("---")

    teacher_name = st.session_state.teacher_name
    current_teachers_db = load_data(TEACHERS_DB_PATH) # Load fresh data for display/edit
    teacher_details = current_teachers_db.get(teacher_name)
    if not teacher_details: st.error("Teacher data not found."); st.stop()

    st.subheader("Manage Class Settings")
    with st.form("edit_teacher_form"):
        st.write("**Class Information**")
        new_subject_en = st.text_input("Subject (English)", value=teacher_details.get("subject_en", ""))
        new_grade = st.text_input("Grade", value=teacher_details.get("grade", ""))
        st.write("**Enrollment Limit**")
        current_cap = teacher_details.get("enrollment_cap") # Could be None
        cap_value = current_cap if current_cap is not None else 0 # Use 0 in number input for None
        new_cap = st.number_input("Maximum Students (0=unlimited)", min_value=0, value=cap_value, step=1, format="%d", key="teacher_edit_cap")
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            processed_cap = int(new_cap) if new_cap > 0 else None # Store None in JSON for unlimited
            current_teachers_db[teacher_name].update({
                "subject_en": new_subject_en.strip(),
                "grade": new_grade.strip(),
                "enrollment_cap": processed_cap
            })
            save_data(TEACHERS_DB_PATH, current_teachers_db)
            teachers_database_global = current_teachers_db # Update global state
            st.success("Settings updated!"); st.rerun()

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
            save_data(TEACHERS_DB_PATH, current_teachers_db)
            teachers_database_global = current_teachers_db # Update global state
            st.success("Class status updated."); st.rerun()

    st.markdown("---")
    st.subheader("Enrollment Overview")
    current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh
    enrolled_students = current_enrollments.get(teacher_name, [])
    enrollment_count = len(enrolled_students)
    display_cap = teacher_details.get("enrollment_cap") # None or int
    cap_text = "Unlimited" if display_cap is None else str(display_cap)
    st.metric("Current Enrollment", f"{enrollment_count} / {cap_text}")
    if enrolled_students:
        st.write("**Enrolled Students:**")
        for i, student_name in enumerate(sorted(enrolled_students), 1): st.markdown(f"{i}. {student_name}")
    else: st.info("No students currently enrolled.")

# --- Teacher Login Page (Hardcoded English) ---
def teacher_login_page():
    if st.session_state.get("teacher_logged_in"): teacher_dashboard(); st.stop()
    st.title("Teacher Portal Login")
    entered_id = st.text_input("Enter your Teacher ID:", type="password", key="teacher_id_input")
    if st.button("Login", key="teacher_login_submit"):
        if not entered_id: st.warning("Please enter ID.")
        else:
            teacher_name, teacher_details = validate_teacher_id(entered_id)
            if teacher_name:
                st.session_state.teacher_logged_in = True
                st.session_state.teacher_id = entered_id
                st.session_state.teacher_name = teacher_name
                st.success(f"Welcome, {teacher_name}!"); st.rerun()
            else: st.error("Invalid Teacher ID.")

# --- Admin Route (WITH EDITORS RE-INTEGRATED) ---
def admin_route():
    # Use global state for admin edits, ensures consistency if app doesn't rerun fully
    global user_database_global, enrollments_global, teachers_database_global

    # Use hardcoded English for Admin panel UI elements
    st.title("Admin Dashboard")
    if "passcode" not in st.secrets: st.error("Admin `passcode` missing."); st.stop()
    admin_password = st.text_input("Enter Admin Password:", type="password", key="admin_pw")
    if not admin_password: st.stop()
    if admin_password != st.secrets["passcode"]: st.error("Incorrect password."); st.stop()
    st.success("Access granted.")

    # Button to explicitly reload data from files if needed
    if st.button("Refresh Data from Files"):
        user_database_global = load_data(USER_DB_PATH)
        enrollments_global = load_data(ENROLLMENTS_DB_PATH)
        teachers_database_global = load_data(TEACHERS_DB_PATH)
        st.rerun()
    st.markdown("---")

    # --- Manage Teachers ---
    st.subheader("Manage Teachers")
    st.markdown("Add/edit details. Set cap=0 for unlimited. Active status managed by teacher. Use trash icon to remove.")
    teachers_list = []
    # Use the global state for initial display, load fresh copy for processing edits
    temp_teachers_db_for_edit = load_data(TEACHERS_DB_PATH)
    needs_saving_defaults = False # Flag if defaults were applied

    for name, details in temp_teachers_db_for_edit.items():
        # Apply defaults if missing (important for robustness)
        if "id" not in details: details["id"] = generate_teacher_id(); needs_saving_defaults = True
        if "is_active" not in details: details["is_active"] = True; needs_saving_defaults = True
        if "enrollment_cap" not in details: details["enrollment_cap"] = None; needs_saving_defaults = True # None for unlimited
        teachers_list.append({
            "Teacher ID": details["id"],
            "Teacher Name": name,
            "Subject (English)": details.get("subject_en", ""), # English only
            "Grade": details.get("grade", ""),
            "Is Active": details.get("is_active"), # Display active status
            "Enrollment Cap": details.get("enrollment_cap") if details.get("enrollment_cap") is not None else 0 # Display 0 for None/unlimited
        })

    # If defaults were added, save the enriched data back immediately
    if needs_saving_defaults:
        save_data(TEACHERS_DB_PATH, temp_teachers_db_for_edit)
        teachers_database_global = temp_teachers_db_for_edit # Update global state
        st.info("Applied default values (ID/Status/Cap) where missing. Data saved.")

    # Create DataFrame for the editor
    if not teachers_list:
        teachers_df = pd.DataFrame(columns=["Teacher ID", "Teacher Name", "Subject (English)", "Grade", "Is Active", "Enrollment Cap"])
    else:
        teachers_df = pd.DataFrame(teachers_list)

    # Configure and display the data editor
    edited_teachers_df = st.data_editor(
        teachers_df,
        num_rows="dynamic",
        key="teacher_editor",
        column_config={
             "Teacher ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
             "Teacher Name": st.column_config.TextColumn("Name", required=True),
             "Subject (English)": st.column_config.TextColumn("Subject EN"),
             "Grade": st.column_config.TextColumn("Grade", width="small"),
             "Is Active": st.column_config.CheckboxColumn("Active?", disabled=True, width="small"), # Display only, managed by teacher
             "Enrollment Cap": st.column_config.NumberColumn("Cap (0=unlimited)", help="Max students. Use 0 for unlimited.", min_value=0, step=1, format="%d", width="small")
        },
        column_order=("Teacher ID", "Teacher Name", "Enrollment Cap", "Subject (English)", "Grade", "Is Active"),
        use_container_width=True
    )

    # Handle saving changes for teachers
    if st.button("Save Changes to Teachers"):
        original_teachers_data = temp_teachers_db_for_edit # Compare against the data loaded for editing
        new_teachers_database = {}
        error_occurred = False
        seen_names = set()
        processed_ids = set()

        for index, row in edited_teachers_df.iterrows():
            name = row["Teacher Name"]
            teacher_id = row["Teacher ID"]
            enrollment_cap_input = row["Enrollment Cap"] # Will be number (or NaN if empty)

            # --- ID Handling ---
            is_new_teacher = pd.isna(teacher_id) or str(teacher_id).strip() == ""
            if is_new_teacher:
                teacher_id = generate_teacher_id()

            # --- Validation ---
            if pd.isna(name) or str(name).strip() == "": st.error(f"Row {index+1}: Name empty."); error_occurred = True; continue
            name = str(name).strip()
            if name in seen_names: st.error(f"Row {index+1}: Duplicate Name '{name}'."); error_occurred = True; continue
            # Check name conflicts with *other* existing IDs
            for existing_name, existing_details in original_teachers_data.items():
                 if existing_details.get("id") != teacher_id and existing_name == name:
                     st.error(f"Row {index+1}: Name '{name}' already used by another teacher ID."); error_occurred = True; break
            if error_occurred: continue
            seen_names.add(name)
            processed_ids.add(teacher_id)

            # --- Process Cap ---
            processed_cap = None # Default to None (unlimited)
            if pd.notna(enrollment_cap_input):
                 try:
                     cap_int = int(enrollment_cap_input)
                     if cap_int > 0: processed_cap = cap_int # Only set if > 0
                 except (ValueError, TypeError): st.error(f"Row {index+1}: Invalid Cap '{enrollment_cap_input}'."); error_occurred = True; continue

            # --- Preserve Active Status ---
            original_details = original_teachers_data.get(name) if not is_new_teacher else None
            current_is_active = original_details.get("is_active", True) if original_details else True # Default new teachers to active

            # --- Build new entry ---
            new_teachers_database[name] = {
                "id": teacher_id,
                "subject_en": str(row["Subject (English)"]) if pd.notna(row["Subject (English)"]) else "",
                "grade": str(row["Grade"]) if pd.notna(row["Grade"]) else "",
                "is_active": current_is_active,
                "enrollment_cap": processed_cap # Store None or int > 0
            }

        # --- Handle Deletions ---
        # Find teachers in the original data whose ID wasn't in the final edited list
        deleted_teacher_names = [n for n, d in original_teachers_data.items() if d.get("id") not in processed_ids]

        # --- Save if no errors ---
        if not error_occurred:
            try:
                save_data(TEACHERS_DB_PATH, new_teachers_database)
                teachers_database_global = new_teachers_database # Update global state
                st.success("Teacher data updated!")

                # Handle enrollments for deleted teachers
                if deleted_teacher_names:
                    enrollments_updated = False
                    current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh
                    new_enrollments_after_delete = current_enrollments.copy()
                    for removed_name in deleted_teacher_names:
                        if removed_name in new_enrollments_after_delete:
                            del new_enrollments_after_delete[removed_name]
                            enrollments_updated = True
                            st.warning(f"Removed enrollments for deleted teacher: {removed_name}")
                    if enrollments_updated:
                         save_data(ENROLLMENTS_DB_PATH, new_enrollments_after_delete)
                         enrollments_global = new_enrollments_after_delete # Update global state
                st.rerun() # Rerun to reflect changes
            except Exception as e: st.error(f"Failed to save teacher data: {e}")
        else: st.warning("Fix errors before saving teacher changes.")

    st.markdown("---")

    # --- Manage Registered Students ---
    st.subheader("Manage Registered Students")
    students_list = []
    temp_user_db_for_edit = load_data(USER_DB_PATH) # Load fresh for editing

    for user_id, user_info in temp_user_db_for_edit.items():
        if isinstance(user_info, dict): # Assumes current structure
            students_list.append({
                "Encrypted ID": user_id,
                "Name": user_info.get("name", ""),
                "Grade": user_info.get("grade", ""),
                "Country": user_info.get("country", ""), # English keys
                "State/Province": user_info.get("state", ""),
                "City": user_info.get("city", "")
            })
        elif isinstance(user_info, str): # Handle old format
            students_list.append({"Encrypted ID": user_id, "Name": user_info, "Grade": "", "Country": "", "State/Province": "", "City": ""})

    # Create DataFrame
    if not students_list:
        students_df = pd.DataFrame(columns=["Encrypted ID", "Name", "Grade", "Country", "State/Province", "City"])
    else:
        students_df = pd.DataFrame(students_list)

    # Display editor
    edited_students_df = st.data_editor(
        students_df,
        num_rows="dynamic",
        key="student_editor",
        column_config={
            "Encrypted ID": st.column_config.TextColumn("Encrypted ID", disabled=True),
            "Name": st.column_config.TextColumn("Student Name", required=True),
            "Grade": st.column_config.TextColumn("Grade"),
            "Country": st.column_config.TextColumn("Country Key"), # Display English keys
            "State/Province": st.column_config.TextColumn("State/Province Key"),
            "City": st.column_config.TextColumn("City Key")
        },
        use_container_width=True
    )

    # Handle saving changes for students
    if st.button("Save Changes to Students"):
        original_ids = set(students_df["Encrypted ID"])
        edited_ids = set(edited_students_df["Encrypted ID"])
        deleted_ids = original_ids - edited_ids

        # Get names of deleted students from the data loaded for editing
        user_db_before_del = temp_user_db_for_edit
        deleted_student_names = set()
        for user_id in deleted_ids:
            info = user_db_before_del.get(user_id)
            if isinstance(info, str): deleted_student_names.add(info)
            elif isinstance(info, dict): deleted_student_names.add(info.get("name", ""))

        new_user_database = {}
        error_occurred = False
        name_changes = {}  # Track old_name -> new_name

        for index, row in edited_students_df.iterrows():
            user_id = row["Encrypted ID"]
            name = row["Name"]
            # --- Validation ---
            if pd.isna(name) or str(name).strip() == "": st.error(f"Row {index+1}: Name empty."); error_occurred = True; continue
            if pd.isna(user_id): st.error(f"Row {index+1}: ID missing."); error_occurred = True; continue # Should not happen

            # --- Clean data ---
            clean_name = str(name).strip()
            clean_grade = str(row["Grade"]).strip() if pd.notna(row["Grade"]) else ""
            clean_country = str(row["Country"]).strip() if pd.notna(row["Country"]) else ""
            clean_state = str(row["State/Province"]).strip() if pd.notna(row["State/Province"]) else ""
            clean_city = str(row["City"]).strip() if pd.notna(row["City"]) else ""

            # --- Build entry ---
            new_user_database[user_id] = {
                "name": clean_name, "grade": clean_grade,
                "country": clean_country, "state": clean_state, "city": clean_city
            }

            # --- Check for name change ---
            old_info = user_db_before_del.get(user_id)
            if old_info:
                old_name = old_info if isinstance(old_info, str) else old_info.get("name", "")
                if old_name and old_name != clean_name: name_changes[old_name] = clean_name

        # --- Save if no errors ---
        if not error_occurred:
            try:
                save_data(USER_DB_PATH, new_user_database)
                user_database_global = new_user_database # Update global state
                st.success("Student data updated!")
                valid_deleted_names = {s for s in deleted_student_names if s} # Filter out empty strings
                if valid_deleted_names: st.info(f"Removed students: {', '.join(valid_deleted_names)}")

                # --- Update enrollments ---
                enrollments_updated = False
                current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh
                new_enrollments = current_enrollments.copy()

                # Handle deletions
                if valid_deleted_names:
                    for teacher, studs in current_enrollments.items():
                        original_length = len(studs)
                        cleaned_list = [s for s in studs if s not in valid_deleted_names]
                        if len(cleaned_list) != original_length:
                            enrollments_updated = True
                            if cleaned_list: new_enrollments[teacher] = cleaned_list
                            elif teacher in new_enrollments: del new_enrollments[teacher] # Remove key if list empty

                # Handle name changes
                if name_changes:
                    for teacher, studs in new_enrollments.items(): # Iterate over potentially modified dict
                        updated_studs = [name_changes.get(s, s) for s in studs]
                        if updated_studs != studs:
                            new_enrollments[teacher] = updated_studs
                            enrollments_updated = True

                # Save enrollments if anything changed
                if enrollments_updated:
                    save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                    enrollments_global = new_enrollments # Update global state
                    st.info("Updated enrollments for deleted/renamed students.")

                st.rerun() # Rerun to reflect changes
            except Exception as e: st.error(f"Failed to save student data: {e}")
        else: st.warning("Fix errors before saving student changes.")

    st.markdown("---")

    # --- Manage Teacher-Student Assignments ---
    st.subheader("Teacher-Student Assignments")
    assignments = []
    current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh data for display
    for teacher, students in current_enrollments.items():
        for student in students:
            assignments.append({"Teacher": teacher, "Student": student})

    # Create DataFrame
    if not assignments: assignments_df = pd.DataFrame(columns=["Teacher", "Student"])
    else: assignments_df = pd.DataFrame(assignments)

    # Get available options from LATEST data
    available_teachers = sorted(list(load_data(TEACHERS_DB_PATH).keys()))
    user_db_for_options = load_data(USER_DB_PATH)
    available_students = sorted([
        (u["name"] if isinstance(u, dict) else u)
        for u in user_db_for_options.values() if (isinstance(u, dict) and u.get("name")) or isinstance(u, str)
    ])

    # Add placeholder if lists are empty to prevent SelectboxColumn error
    if not available_teachers: available_teachers = ["(No teachers available)"]
    if not available_students: available_students = ["(No students available)"]

    # Display editor
    edited_assignments = st.data_editor(
        assignments_df,
        num_rows="dynamic",
        key="assignment_editor",
        column_config={
            "Teacher": st.column_config.SelectboxColumn("Teacher", options=available_teachers, required=True),
            "Student": st.column_config.SelectboxColumn("Student", options=available_students, required=True)
        },
        use_container_width=True
    )

    # Handle saving assignments
    if st.button("Save Changes to Assignments"):
        new_enrollments = {}
        error_occurred = False
        processed_pairs = set()
        # Reload options just before saving for validation
        latest_teachers = list(load_data(TEACHERS_DB_PATH).keys())
        latest_user_db = load_data(USER_DB_PATH)
        latest_students = [(u["name"] if isinstance(u, dict) else u) for u in latest_user_db.values() if (isinstance(u, dict) and u.get("name")) or isinstance(u, str)]

        for index, row in edited_assignments.iterrows():
            teacher, student = row["Teacher"], row["Student"]
            # --- Validation ---
            if pd.isna(teacher) or str(teacher).strip() == "": st.error(f"Row {index+1}: Teacher empty."); error_occurred = True; continue
            if pd.isna(student) or str(student).strip() == "": st.error(f"Row {index+1}: Student empty."); error_occurred = True; continue
            teacher, student = str(teacher).strip(), str(student).strip()

            # Check against latest available options
            if teacher not in latest_teachers: st.error(f"Row {index+1}: Teacher '{teacher}' no longer exists."); error_occurred = True; continue
            if student not in latest_students: st.error(f"Row {index+1}: Student '{student}' no longer exists."); error_occurred = True; continue

            # Check for duplicates within the submission
            if (teacher, student) in processed_pairs:
                st.warning(f"Row {index+1}: Duplicate assignment {student} to {teacher} ignored.")
                continue
            processed_pairs.add((teacher, student))

            # --- Build new enrollments ---
            if teacher not in new_enrollments: new_enrollments[teacher] = []
            if student not in new_enrollments[teacher]: new_enrollments[teacher].append(student)

        # --- Save if no errors ---
        if not error_occurred:
            try:
                # Sort student lists for consistency before saving
                for teacher in new_enrollments: new_enrollments[teacher].sort()
                save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                enrollments_global = new_enrollments # Update global state
                st.success("Assignments updated!")
                st.rerun() # Rerun to reflect changes
            except Exception as e: st.error(f"Failed to save assignments: {e}")
        else: st.warning("Fix errors before saving assignments.")

# --- Main Application Logic ---
params = st.query_params
plain_id = params.get("id", "")
if isinstance(plain_id, list): plain_id = plain_id[0] if plain_id else ""
if not plain_id: st.error("No user id provided (?id=...)"); st.stop()

request_id = plain_id.lower()

# --- Routing ---
if request_id == "admin":
    admin_route() # Assuming placeholder logic is replaced
elif request_id == "teacher":
    teacher_login_page()
else:
    # --- STUDENT/USER PATH ---
    selected_language = st.sidebar.selectbox(
        "Language / 语言", # Static label
        options=["English", "中文"],
        key="lang_select",
    )

    # --- Select the appropriate language dictionary DIRECTLY ---
    lang = texts.get(selected_language, texts["English"]) # Default to English
    lang_code = 'en' if selected_language == 'English' else 'zh-cn' # For dynamic translation

    secure_id = request_id
    st.markdown(f"""<script>document.title = "{lang['page_title']}";</script>""", unsafe_allow_html=True)

    # --- Define format_location HERE, before the registration check ---
    # It needs selected_language, translator, translate_dynamic_text, lang_code
    def format_location(location_name):
        """Translates location name for display if needed."""
        if selected_language == "English" or not translator:
            return location_name # Return original English name
        # Only translate if Chinese is selected AND translator is available
        return translate_dynamic_text(translator, location_name, lang_code)
    # --- End format_location definition ---

    # --- Reload data for user path ---
    user_database = load_data(USER_DB_PATH)
    teachers_database = load_data(TEACHERS_DB_PATH)
    enrollments = load_data(ENROLLMENTS_DB_PATH)

    # --- REGISTRATION Section ---
    if secure_id not in user_database:
        st.title(lang["page_title"])
        st.write(lang["register_prompt"])

        new_user_name = st.text_input(lang["register_name_label"], key="register_input")
        new_user_grade = st.text_input(lang["register_grade_label"], key="register_grade")

        # Location Dropdowns can now use format_location defined above
        country_options = [lang["select_country"]] + sorted(location_data.keys())
        selected_country = st.selectbox(lang["register_country_label"], options=country_options, key="reg_country", index=0, format_func=format_location)

        state_options = [lang["select_state"]]
        if selected_country != lang["select_country"] and selected_country in location_data:
            state_options.extend(sorted(location_data[selected_country].keys()))
        selected_state = st.selectbox(lang["register_state_label"], options=state_options, key="reg_state", index=0, disabled=(selected_country == lang["select_country"]), format_func=format_location)

        city_options = [lang["select_city"]]
        if selected_state != lang["select_state"] and selected_country in location_data and selected_state in location_data[selected_country]:
            city_options.extend(sorted(location_data[selected_country][selected_state]))
        selected_city = st.selectbox(lang["register_city_label"], options=city_options, key="reg_city", index=0, disabled=(selected_state == lang["select_state"]), format_func=format_location)

        st.markdown("---")

        if st.button(lang["register_button"], key="register_btn"):
             # ... (rest of registration button logic - unchanged) ...
             if new_user_name.strip() and selected_country != lang["select_country"] and selected_state != lang["select_state"] and selected_city != lang["select_city"]:
                user_data_to_save = {
                    "name": new_user_name.strip(),
                    "grade": new_user_grade.strip(),
                    "country": selected_country, # Save English key
                    "state": selected_state,     # Save English key
                    "city": selected_city        # Save English key
                }
                user_database[secure_id] = user_data_to_save
                save_data(USER_DB_PATH, user_database)
                st.success(lang["registered_success"].format(name=new_user_name.strip()))
                st.balloons(); time.sleep(1); st.rerun()
             else: st.error(lang["fill_all_fields"])
        st.stop()

    # --- MAIN ENROLLMENT Section ---
    # This section runs when the user IS registered
    user_info = user_database.get(secure_id)
    if isinstance(user_info, dict): user_name = user_info.get("name", "Unknown")
    elif isinstance(user_info, str): user_name = user_info # Old format
    else: user_name = "Unknown"; st.sidebar.error("User data error.")

    st.sidebar.write(lang["logged_in"].format(name=user_name))

    # --- This line can NOW find format_location ---
    if isinstance(user_info, dict):
        c, s, ci = user_info.get("country"), user_info.get("state"), user_info.get("city")
        # Check if location data exists before trying to format it
        if c and s and ci:
            st.sidebar.caption(f"{format_location(ci)}, {format_location(s)}, {format_location(c)}")

    st.title(lang["page_title"])
    if st.sidebar.button(lang["refresh"]): st.rerun()

    # --- Teacher Search and Filter ---
    st.subheader(lang["teacher_search_label"])
    col_search, col_grade_filter = st.columns([3, 2])
    with col_search: teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter", label_visibility="collapsed")

    active_teachers = {n: i for n, i in teachers_database.items() if i.get("is_active", True)}
    unique_grades = sorted(list({str(i.get("grade","")).strip() for i in active_teachers.values() if str(i.get("grade","")).strip()}))
    grade_options = [lang["all_grades"]] + unique_grades
    with col_grade_filter: selected_grade_filter = st.selectbox(lang["grade_select_label"], options=grade_options, key="grade_select")

    # --- Filtering Logic ---
    filtered_teachers = {}
    if active_teachers:
        term = teacher_filter.strip().lower()
        for n, i in active_teachers.items():
            name_match = (not term) or (term in n.lower())
            grade_match = (selected_grade_filter == lang["all_grades"]) or (str(i.get("grade","")).strip() == selected_grade_filter)
            if name_match and grade_match: filtered_teachers[n] = i

    st.markdown("---")

    # --- Display Teachers ---
    if not active_teachers: st.warning(lang["no_teachers_available"])
    elif not filtered_teachers: st.error(lang["teacher_not_found_error"])
    else:
        for teacher_name, teacher_info in filtered_teachers.items():
            st.subheader(teacher_name)

            # Dynamically translate subject for display if needed
            subject_en = teacher_info.get("subject_en", "N/A")
            display_subject = subject_en
            if selected_language != "English" and translator:
                display_subject = translate_dynamic_text(translator, subject_en, lang_code)
            grade = teacher_info.get("grade", "N/A")

            desc_parts = []
            if display_subject != "N/A": desc_parts.append(f"**{display_subject}**")
            if grade != "N/A": desc_parts.append(f"({lang['to_grade']} **{grade}**)")
            st.write(f"{lang['teaches']} {' '.join(desc_parts)}" if desc_parts else f"({lang['teaches']} N/A)")

            # Enrollment status
            current_teacher_enrollments = enrollments.get(teacher_name, [])
            count = len(current_teacher_enrollments)
            cap = teacher_info.get("enrollment_cap") # None or int
            cap_text = lang["unlimited"] if cap is None else str(cap)
            is_full = False if cap is None else count >= cap
            st.caption(lang["user_enrollment_caption"].format(count=count, cap=cap_text))

            col1, col2 = st.columns(2)
            is_enrolled = user_name in current_teacher_enrollments

            # Enroll/Cancel Buttons
            with col1:
                enroll_label = lang["enrollment_full"] if is_full and not is_enrolled else lang["enroll_button"]
                enroll_disabled = is_enrolled or is_full
                enroll_clicked = st.button(enroll_label, key=f"enroll_{teacher_name}", disabled=enroll_disabled, use_container_width=True)
            with col2:
                cancel_clicked = st.button(lang["cancel_button"], key=f"cancel_{teacher_name}", disabled=not is_enrolled, use_container_width=True)

            # Button Actions (with re-check on click)
            if enroll_clicked:
                enrollments_now = load_data(ENROLLMENTS_DB_PATH)
                teacher_list_now = enrollments_now.get(teacher_name, [])
                teacher_info_now = load_data(TEACHERS_DB_PATH).get(teacher_name, {})
                cap_now = teacher_info_now.get("enrollment_cap")
                is_full_now = False if cap_now is None else len(teacher_list_now) >= cap_now
                if user_name not in teacher_list_now and not is_full_now:
                    teacher_list_now.append(user_name)
                    enrollments_now[teacher_name] = teacher_list_now
                    save_data(ENROLLMENTS_DB_PATH, enrollments_now)
                    st.success(lang["enroll_success"].format(name=user_name, teacher=teacher_name))
                    st.rerun()
                # No explicit else needed, button should be disabled

            if cancel_clicked:
                enrollments_now = load_data(ENROLLMENTS_DB_PATH)
                if teacher_name in enrollments_now and user_name in enrollments_now[teacher_name]:
                    enrollments_now[teacher_name].remove(user_name)
                    if not enrollments_now[teacher_name]: del enrollments_now[teacher_name]
                    save_data(ENROLLMENTS_DB_PATH, enrollments_now)
                    st.info(lang["enrollment_cancelled"])
                    st.rerun()
                # No explicit else needed, button should be disabled

            # Enrollment List Expander
            with st.expander(f"{lang['enrolled_label']} ({count})"):
                if current_teacher_enrollments:
                    for i, name in enumerate(sorted(current_teacher_enrollments), 1):
                        marker = f" **({lang['you_marker']})**" if name == user_name else ""
                        st.markdown(f"{i}. {name}{marker}")
                else: st.write(lang["no_enrollments"])
            st.markdown("---")
