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
from streamlit_star_rating import st_star_rating
from googletrans import Translator, LANGUAGES # Using googletrans (unofficial)

# --- Translation Setup (ONLY for dynamic content) ---
try:
    translator = Translator(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
except Exception as e:
    st.error(f"Translator init failed: {e}. Location/Subject translation may fail.")
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
        "no_teachers_available": "No teachers are currently available for enrollment.", "enrollment_full": "Enrollment Full","enrollment_closed": "Enrollment Closed",
        "user_enrollment_caption": "Enrolled: {count} / {cap}", "unlimited": "Unlimited", "grade_select_label": "Select Grade",
        "all_grades": "All", "refresh": "Refresh", "register_name_label": "Student's English Full Name", "register_grade_label": "Current Grade",
        "register_raz_label": "RAZ Level", # <-- Added RAZ Label
        "register_country_label": "Country", "register_state_label": "State/Province", "register_city_label": "City",
        "select_country": "--- Select Country ---", "select_state": "--- Select State/Province ---", "select_city": "--- Select City ---",
        "fill_all_fields": "Please fill in Name and select a valid Country, State/Province, and City.", # RAZ not mandatory here, adjust if needed
        "already_enrolled_warning": "Already enrolled.", "registered_success": "Registered {name}! Reloading page.", "you_marker": "You",
        "save_settings_button": "Save Settings", "settings_updated_success": "Settings updated successfully!", "class_info_header": "Class Information",
        "subject_en_label": "Subject (English)", "grade_label": "Grade", "enrollment_limit_header": "Enrollment Limit",
        "max_students_label": "Maximum Students (0=unlimited)", "class_status_header": "Class Status","class_rating": "Class Rating","class_no_rating": "No Ratings Yet", "enrollment_status_header": "Enrollment Status",
        "status_active": "Active (Students can see)", "status_cancelled": "Cancelled (Students cannot see)","enrollment_active": "Open (Students can enroll)","enrollment_blocked": "Closed (Students cannot enroll)",
        "cancel_class_button": "Cancel Class (Hide)", "reactivate_class_button": "Reactivate Class (Show)","block_enroll_button": "Close Enrollment", "reactivate_enroll_button": "Open Enrollment",
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
        "teacher_description_label_en": "Description (English)",
        "teacher_description_label_zh": "Description (Chinese)",
        "teacher_description_header": "Teacher Description",
        "no_description_available": "No description available.", # For Student View
        "admin_manage_teachers_desc_en": "Description EN", # Column header in Admin
        "admin_manage_teachers_desc_zh": "Description ZH", # 
    },
    "中文": {
        "page_title": "PLE Youth 教师搜索与注册", "language_label": "选择语言", "teacher_search_label": "请输入教师姓名搜索：",
        "teacher_not_found_error": "没有匹配的可用教师。", "enter_teacher_info": "正在显示所有可用教师。使用上方搜索框筛选。",
        "teaches": "授课", "to_grade": "年级", "enroll_button": "报名", "cancel_button": "取消报名",
        "enroll_success": "谢谢, {name}! 你已注册到 {teacher} 的课程！", "enrollment_cancelled": "报名已取消。",
        "register_prompt": "欢迎！请通过输入学生的详细信息完成注册：", "register_button": "注册",
        "logged_in": "已登录: {name}", "enrolled_label": "已报名的学生", "no_enrollments": "当前没有报名的学生。",
        "not_enrolled": "未找到你的报名记录。", "name_required": "请输入你的名字以注册。",
        "no_teachers_available": "目前没有可报名的教师。", "enrollment_full": "报名已满","enrollment_closed": "报名关闭",
        "user_enrollment_caption": "已报名: {count} / {cap}", "unlimited": "无限制", "grade_select_label": "选择年级",
        "all_grades": "所有年级", "refresh": "刷新", "register_name_label": "学生英文全名", "register_grade_label": "当前年级",
        "register_raz_label": "RAZ 等级", # <-- Added RAZ Label
        "register_country_label": "国家", "register_state_label": "州/省", "register_city_label": "城市",
        "select_country": "--- 选择国家 ---", "select_state": "--- 选择州/省 ---", "select_city": "--- 选择城市 ---",
        "fill_all_fields": "请填写姓名并选择有效的国家、州/省和城市。", # RAZ not mandatory here, adjust if needed
        "already_enrolled_warning": "已报名。", "registered_success": "已注册 {name}! 正在重新加载页面。", "you_marker": "你",
        "save_settings_button": "保存设置", "settings_updated_success": "设置已成功更新！", "class_info_header": "课程信息",
        "subject_en_label": "科目（英文）", "grade_label": "年级", "enrollment_limit_header": "报名人数限制",
        "max_students_label": "最多学生数（0表示无限制）", "class_status_header": "课程状态","class_rating": "课程评分","class_no_rating": "还没有评分","enrollment_status_header": "报名状态",
        "status_active": "开放（学生可以看到）", "status_cancelled": "已取消（学生无法看到）","enrollment_active": "开放（学生可以报名）","enrollment_blocked": "关闭（学生不可以报名）",
        "cancel_class_button": "取消课程（隐藏）", "reactivate_class_button": "重新激活课程（显示）","block_enroll_button": "关闭报名", "reactivate_enroll_button": "开放报名",
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
        "teacher_description_label_en": "描述（英文）",
        "teacher_description_label_zh": "描述（中文）",
        "teacher_description_header": "教师描述", # 教师仪表板部分
        "no_description_available": "暂无描述。", # 学生视图
        "admin_manage_teachers_desc_en": "描述 EN", # 管理员中的列标题
        "admin_manage_teachers_desc_zh": "描述 ZH", # 管理员中的列标题
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

# --- Teacher Dashboard (Displaying Names from IDs) ---
def teacher_dashboard():
    global teachers_database_global, enrollments_global
    admin_lang = texts["English"] # Teacher dashboard uses English UI elements for now

    # ... (Title, Logout, Refresh, Teacher Details Loading - unchanged) ...
    st.title(f"{admin_lang['teacher_dashboard_title'].format(name=st.session_state.teacher_name)}")
    if st.button(admin_lang["teacher_logout_button"], key="teacher_logout"):
        keys_to_delete = ["teacher_logged_in", "teacher_id", "teacher_name"]
        for key in keys_to_delete:
            if key in st.session_state: del st.session_state[key]
        st.success("Logged out."); st.rerun()
    if st.button(admin_lang["refresh"]): st.rerun()
    st.markdown("---")
    teacher_name = st.session_state.teacher_name
    current_teachers_db = load_data(TEACHERS_DB_PATH)
    teacher_details = current_teachers_db.get(teacher_name)
    if not teacher_details: st.error("Teacher data not found."); st.stop()
    ratt=teacher_details.get("rating",None)
    if (ratt != None and ratt.isdigit() and int(ratt)>=0):
        st_star_rating(label = admin_lang["class_rating"], maxValue = 5, defaultValue = int(teacher_details.get("rating","0")), key = "rating", read_only = True )
    else:
        st.subheader(admin_lang["class_rating"])
        st.info(admin_lang["class_no_rating"])
    # ... (Class Status display and buttons - unchanged) ...
    st.subheader(admin_lang["class_status_header"])
    is_active = teacher_details.get("is_active", True)
    
    status_text = admin_lang["status_active"] if is_active else admin_lang["status_cancelled"]
    if is_active:
        st.success(f"Class Status: {status_text}")
    else:
        st.warning(f"Class Status: {status_text}")
        
    btn_label = admin_lang["cancel_class_button"] if is_active else admin_lang["reactivate_class_button"]
    btn_key = "cancel_class_btn" if is_active else "reactivate_class_btn"
    new_status = not is_active
    if st.button(btn_label, key=btn_key):
            current_teachers_db[teacher_name]["is_active"] = new_status
            save_data(TEACHERS_DB_PATH, current_teachers_db); teachers_database_global = current_teachers_db
            st.success("Class status updated."); st.rerun()

    st.subheader(admin_lang["enrollment_status_header"])
    allow_enr = teacher_details.get("allow_enroll", True)
    status_text = admin_lang["enrollment_active"] if allow_enr else admin_lang["enrollment_blocked"]
    if allow_enr:
        st.success(f"Enrollment Status: {status_text}")
    else:
        st.warning(f"Enrollment Status: {status_text}")
    
    btn_label1 = admin_lang["block_enroll_button"] if allow_enr else admin_lang["reactivate_enroll_button"]
    btn_key1 = "block_enroll_btn" if allow_enr else "reactivate_enroll_btn"
    new_status1 = not allow_enr
    if st.button(btn_label1, key=btn_key1):
            current_teachers_db[teacher_name]["allow_enroll"] = new_status1
            save_data(TEACHERS_DB_PATH, current_teachers_db); teachers_database_global = current_teachers_db
            st.success("Enrollment status updated."); st.rerun()

    # ... (Class Settings Form - unchanged) ...
    st.markdown("---")
    st.subheader(admin_lang["class_info_header"])
    with st.form("edit_teacher_form"):
        # ... (Subject, Grade, Cap, Descriptions inputs - unchanged) ...
        st.write("**Class Details & Limit**"); col1, col2 = st.columns(2)
        with col1: new_subject_en = st.text_input(admin_lang["subject_en_label"], value=teacher_details.get("subject_en", ""))
        with col2: new_grade = st.text_input(admin_lang["grade_label"], value=teacher_details.get("grade", ""))
        current_cap = teacher_details.get("enrollment_cap"); cap_value = current_cap if current_cap is not None else 0
        new_cap = st.number_input(admin_lang["max_students_label"], min_value=0, value=cap_value, step=1, format="%d", key="teacher_edit_cap")
        st.markdown("---"); st.write(f"**{admin_lang['teacher_description_header']}**")
        new_desc_en = st.text_area(admin_lang["teacher_description_label_en"], value=teacher_details.get("description_en", ""), height=150)
        new_desc_zh = st.text_area(admin_lang["teacher_description_label_zh"], value=teacher_details.get("description_zh", ""), height=150)
        # ... (Save button logic - unchanged) ...
        submitted = st.form_submit_button(admin_lang["save_settings_button"])
        if submitted:
            processed_cap = int(new_cap) if new_cap > 0 else None
            current_teachers_db[teacher_name].update({"subject_en": new_subject_en.strip(),"grade": new_grade.strip(),"enrollment_cap": processed_cap,"description_en": new_desc_en.strip(),"description_zh": new_desc_zh.strip()})
            save_data(TEACHERS_DB_PATH, current_teachers_db); teachers_database_global = current_teachers_db
            st.success(admin_lang["settings_updated_success"]); st.rerun()


    st.markdown("---")
    st.subheader(admin_lang["enrollment_overview_header"])
    # --- Enrollment Overview (Displaying names looked up by ID) ---
    current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh enrollments (student IDs)
    user_db_for_display = load_data(USER_DB_PATH)     # Load fresh user data for name lookup

    enrolled_student_ids = current_enrollments.get(teacher_name, [])
    enrollment_count = len(enrolled_student_ids)
    display_cap = teacher_details.get("enrollment_cap") # None or int
    cap_text = admin_lang["unlimited"] if display_cap is None else str(display_cap)
    st.metric(admin_lang["current_enrollment_metric"], f"{enrollment_count} / {cap_text}")

    if enrolled_student_ids:
        st.write(f"**{admin_lang['enrolled_students_list_header']}**")
        # Create a list of names looked up from IDs
        enrolled_student_names = []
        for s_id in enrolled_student_ids:
            student_info = user_db_for_display.get(s_id)
            if isinstance(student_info, dict):
                enrolled_student_names.append(student_info.get("name", f"Unknown ID: {s_id}"))
            elif isinstance(student_info, str): # Handle old format if necessary
                 enrolled_student_names.append(f"{student_info} (ID: {s_id})")
            else:
                 enrolled_student_names.append(f"Unknown ID: {s_id}")

        # Display sorted names
        for i, student_name_display in enumerate(sorted(enrolled_student_names), 1):
            st.markdown(f"{i}. {student_name_display}")
    else:
        st.info(admin_lang["no_enrollments"])
# --- Admin Route (Updated for Teacher Description) ---
def admin_route():
    global user_database_global, enrollments_global, teachers_database_global
    admin_lang = texts["English"] # Admin panel uses English UI text

    st.title(admin_lang["admin_dashboard_title"])
    # ... (Password check, Refresh Button - unchanged) ...
    if "passcode" not in st.secrets: st.error("Admin `passcode` missing."); st.stop()
    admin_password = st.text_input(admin_lang["admin_password_prompt"], type="password", key="admin_pw")
    if not admin_password: st.stop()
    if admin_password != st.secrets["passcode"]: st.error("Incorrect password."); st.stop()
    st.success(admin_lang["admin_access_granted"])
    if st.button(admin_lang["refresh_data_button"]):
        user_database_global = load_data(USER_DB_PATH); enrollments_global = load_data(ENROLLMENTS_DB_PATH); teachers_database_global = load_data(TEACHERS_DB_PATH)
        st.rerun()
    st.markdown("---")

    # --- Manage Teachers (Unchanged) ---
    st.subheader(admin_lang["manage_teachers_header"])
    st.markdown(admin_lang["manage_teachers_info"])
    # ... (Teacher editor and save logic - unchanged from previous version) ...
    # Data loading and preparation
    teachers_list = []; temp_teachers_db_for_edit = load_data(TEACHERS_DB_PATH); needs_saving_defaults = False
    for name, details in temp_teachers_db_for_edit.items():
        if "id" not in details: details["id"] = generate_teacher_id(); needs_saving_defaults = True
        if "is_active" not in details: details["is_active"] = True; needs_saving_defaults = True
        if "enrollment_cap" not in details: details["enrollment_cap"] = None; needs_saving_defaults = True
        if "description_en" not in details: details["description_en"] = ""; needs_saving_defaults = True
        if "description_zh" not in details: details["description_zh"] = ""; needs_saving_defaults = True
        if "rating" not in details: details["rating"] = None; needs_saving_defaults = True
        if "allow_enroll" not in details: details["allow_enroll"] = True; needs_saving_defaults = True
        teachers_list.append({"Teacher ID": details["id"],"Teacher Name": name,"Subject (English)": details.get("subject_en", ""),"Description (English)": details.get("description_en", ""),"Description (Chinese)": details.get("description_zh", ""),"Grade": details.get("grade", ""),"Is Active": details.get("is_active"),"Rating": details.get("rating"),"Allow Enroll":details.get("allow_enroll"),"Enrollment Cap": details.get("enrollment_cap") if details.get("enrollment_cap") is not None else 0})
    if needs_saving_defaults: save_data(TEACHERS_DB_PATH, temp_teachers_db_for_edit); teachers_database_global = temp_teachers_db_for_edit; st.info("Applied defaults to teachers. Data saved.")
    columns_teacher = ["Teacher ID", "Teacher Name", "Enrollment Cap", "Subject (English)", "Grade", "Description (English)", "Description (Chinese)", "Rating","Allow Enroll", "Is Active"]; teachers_df = pd.DataFrame(teachers_list, columns=columns_teacher) if teachers_list else pd.DataFrame(columns=columns_teacher)
    # Teacher editor UI
    edited_teachers_df = st.data_editor(teachers_df,num_rows="dynamic",key="teacher_editor",use_container_width=True,hide_index=True,
        column_config={"Teacher ID": st.column_config.TextColumn("ID", disabled=True),"Teacher Name": st.column_config.TextColumn("Name", required=True),"Subject (English)": st.column_config.TextColumn("Subject EN"),"Description (English)": st.column_config.TextColumn(admin_lang["admin_manage_teachers_desc_en"]),"Description (Chinese)": st.column_config.TextColumn(admin_lang["admin_manage_teachers_desc_zh"]),"Grade": st.column_config.TextColumn("Grade"),"Rating": st.column_config.TextColumn("Class Rating"),"Allow Enroll": st.column_config.CheckboxColumn("Allow Enroll?"),"Is Active": st.column_config.CheckboxColumn("Active?"),"Enrollment Cap": st.column_config.NumberColumn("Cap (0=unlimited)", min_value=0, step=1, format="%d")},
        column_order=columns_teacher)
    # Teacher save logic
    if st.button(admin_lang["save_teachers_button"]):
        # ... (Teacher saving logic identical to previous version) ...
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
                 except (ValueError, TypeError): st.error(f"Row {index+1}: Invalid Cap."); error_occurred = True; continue
            original_details = next((d for _, d in original_teachers_data.items() if d.get("id") == teacher_id), None); current_is_active = original_details.get("is_active", True) if original_details else True

            desc_en = str(row["Description (English)"]).strip() if pd.notna(row["Description (English)"]) else ""; desc_zh = str(row["Description (Chinese)"]).strip() if pd.notna(row["Description (Chinese)"]) else ""
            rat=row["Rating"]
            if (row["Allow Enroll"]==None):
                allow_enroll=True
            else:
                allow_enroll=row["Allow Enroll"]
            new_teachers_database[name] = {"id": teacher_id,"subject_en": str(row["Subject (English)"]) if pd.notna(row["Subject (English)"]) else "","grade": str(row["Grade"]) if pd.notna(row["Grade"]) else "","description_en": desc_en,"description_zh": desc_zh,"is_active": current_is_active,"allow_enroll":allow_enroll,"enrollment_cap": processed_cap,"rating":rat}
        deleted_teacher_names = [n for n, d in original_teachers_data.items() if d.get("id") not in processed_ids]
        if not error_occurred:
            try:
                save_data(TEACHERS_DB_PATH, new_teachers_database); teachers_database_global = new_teachers_database; st.success("Teacher data updated!")
                if deleted_teacher_names:
                    enrollments_updated = False; current_enrollments = load_data(ENROLLMENTS_DB_PATH); new_enrollments_after_delete = current_enrollments.copy()
                    for removed_name in deleted_teacher_names:
                        if removed_name in new_enrollments_after_delete: del new_enrollments_after_delete[removed_name]; enrollments_updated = True; st.warning(f"Removed enrollments: {removed_name}")
                    if enrollments_updated: save_data(ENROLLMENTS_DB_PATH, new_enrollments_after_delete); enrollments_global = new_enrollments_after_delete
                st.rerun()
            except Exception as e: st.error(f"Failed to save teacher data: {e}")
        else: st.warning("Fix errors before saving teacher changes.")

    st.markdown("---")

    # --- Manage Registered Students (Update enrollment removal logic) ---
    st.subheader(admin_lang["manage_students_header"])
    # ... (Student list preparation and editor display - unchanged) ...
    students_list = []; temp_user_db_for_edit = load_data(USER_DB_PATH)
    for user_id, user_info in temp_user_db_for_edit.items():
        if isinstance(user_info, dict): students_list.append({"Encrypted ID": user_id,"Name": user_info.get("name", ""),"Grade": user_info.get("grade", ""),"RAZ Level": user_info.get("raz_level", ""),"Country": user_info.get("country", ""),"State/Province": user_info.get("state", ""),"City": user_info.get("city", "")})
        elif isinstance(user_info, str): students_list.append({"Encrypted ID": user_id, "Name": user_info, "Grade": "", "RAZ Level": "", "Country": "", "State/Province": "", "City": ""})
    students_df = pd.DataFrame(students_list) if students_list else pd.DataFrame(columns=["Encrypted ID", "Name", "Grade", "RAZ Level", "Country", "State/Province", "City"])
    edited_students_df = st.data_editor(students_df,num_rows="dynamic",key="student_editor",use_container_width=True,
        column_config={"Encrypted ID": st.column_config.TextColumn(disabled=True),"Name": st.column_config.TextColumn(required=True),"Grade": st.column_config.TextColumn(),"RAZ Level": st.column_config.TextColumn(),"Country": st.column_config.TextColumn("Country Key"),"State/Province": st.column_config.TextColumn("State/Prov Key"),"City": st.column_config.TextColumn("City Key")},
        column_order=["Encrypted ID", "Name", "Grade", "RAZ Level", "Country", "State/Province", "City"])

    # Handle saving changes for students
    if st.button(admin_lang["save_students_button"]):
        original_ids = set(students_df["Encrypted ID"])
        edited_ids = set(edited_students_df["Encrypted ID"])
        deleted_ids = original_ids - edited_ids # These are the IDs to remove from enrollments

        user_db_before_del = temp_user_db_for_edit # Get names for info message
        deleted_student_names = {info.get("name", "") if isinstance(info, dict) else info for uid, info in user_db_before_del.items() if uid in deleted_ids and info}

        new_user_database = {}; error_occurred = False
        # name_changes no longer needed for enrollment updates

        for index, row in edited_students_df.iterrows():
             # ... (Processing each row to build new_user_database - unchanged, includes RAZ) ...
            user_id = row["Encrypted ID"]; name = row["Name"]
            if pd.isna(name) or str(name).strip() == "": st.error(f"Row {index+1}: Name empty."); error_occurred = True; continue
            if pd.isna(user_id): st.error(f"Row {index+1}: ID missing."); error_occurred = True; continue
            clean_name=str(name).strip();clean_grade=str(row["Grade"]).strip() if pd.notna(row["Grade"]) else "";clean_raz=str(row["RAZ Level"]).strip() if pd.notna(row["RAZ Level"]) else "";clean_country=str(row["Country"]).strip() if pd.notna(row["Country"]) else "";clean_state=str(row["State/Province"]).strip() if pd.notna(row["State/Province"]) else "";clean_city=str(row["City"]).strip() if pd.notna(row["City"]) else ""
            new_user_database[user_id] = {"name": clean_name, "grade": clean_grade, "raz_level": clean_raz,"country": clean_country, "state": clean_state, "city": clean_city}
            # No need to track name_changes for enrollments anymore

        if not error_occurred:
            try:
                save_data(USER_DB_PATH, new_user_database)
                user_database_global = new_user_database
                st.success("Student data updated!")
                valid_deleted_names = {s for s in deleted_student_names if s}
                if valid_deleted_names: st.info(f"Removed students: {', '.join(valid_deleted_names)}")

                # --- Update enrollments: Remove deleted IDs ---
                if deleted_ids: # Only run if students were actually deleted
                    enrollments_updated = False
                    current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh
                    new_enrollments = current_enrollments.copy()

                    for teacher, student_id_list in current_enrollments.items():
                        original_length = len(student_id_list)
                        # Keep only IDs NOT in the deleted_ids set
                        cleaned_id_list = [s_id for s_id in student_id_list if s_id not in deleted_ids]

                        if len(cleaned_id_list) != original_length:
                            enrollments_updated = True
                            if cleaned_list:
                                new_enrollments[teacher] = cleaned_id_list
                            # Remove teacher key if list becomes empty
                            elif teacher in new_enrollments:
                                del new_enrollments[teacher]

                    if enrollments_updated:
                        save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                        enrollments_global = new_enrollments # Update global state
                        st.info("Updated enrollments for deleted students.")
                        # Name change logic is removed as it's no longer needed

                st.rerun() # Rerun to reflect changes
            except Exception as e: st.error(f"Failed to save student data: {e}")
        else: st.warning("Fix errors before saving student changes.")

    st.markdown("---")

    # --- Manage Teacher-Student Assignments (READ-ONLY VIEW) ---
    st.subheader(admin_lang["manage_assignments_header"])
    st.markdown("*(Read-Only View - Manage enrollments via student deletion or student login)*") # Clarify it's read-only
    assignments_list_enriched = []
    current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh (contains IDs)
    user_db_for_assignments = load_data(USER_DB_PATH) # Load fresh user data

    # Build the enriched list for the DataFrame
    for teacher, student_id_list in current_enrollments.items():
        for student_id in student_id_list:
            details = user_db_for_assignments.get(student_id) # Lookup by ID
            if isinstance(details, dict): # Found details
                student_name = details.get("name", f"Unknown ID: {student_id}")
                location_str = f"{details.get('city', '')}, {details.get('state', '')}, {details.get('country', '')}".strip(", ")
                assignments_list_enriched.append({
                    "Teacher": teacher,
                    "Student": student_name, # Display name
                    "Grade": details.get("grade", ""),
                    admin_lang["raz_level_column"]: details.get("raz_level", ""),
                    admin_lang["location_column"]: location_str if location_str != "," else "",
                    "_Student ID": student_id # Keep ID internally if needed later, hide from view
                })
            else: # Student ID exists in enrollment but not in user_db? Data inconsistency.
                 assignments_list_enriched.append({
                    "Teacher": teacher, "Student": f"Missing User Data (ID: {student_id})", "Grade": "N/A",
                    admin_lang["raz_level_column"]: "N/A", admin_lang["location_column"]: "N/A",
                     "_Student ID": student_id
                })

    # Create DataFrame from the enriched list
    assign_cols = ["Teacher", "Student", "Grade", admin_lang["raz_level_column"], admin_lang["location_column"]]
    assignments_df = pd.DataFrame(assignments_list_enriched, columns=assign_cols) if assignments_list_enriched else pd.DataFrame(columns=assign_cols)

    # Display the DataFrame as a table (read-only)
    st.dataframe(
        assignments_df,
        column_config={ # Define headers, widths etc. Still useful for display formatting.
            "Teacher": st.column_config.TextColumn(width="medium"),
            "Student": st.column_config.TextColumn(width="medium"),
            "Grade": st.column_config.TextColumn(width="small"),
            admin_lang["raz_level_column"]: st.column_config.TextColumn(width="small"),
            admin_lang["location_column"]: st.column_config.TextColumn(width="large"),
        },
        use_container_width=True,
        hide_index=True,
    )
    st.markdown("---")

    st.subheader("Batch Actions (Proceed with Caution)")
    if "all_closed" not in st.session_state:
        st.session_state.all_closed=False
    if "all_hidden" not in st.session_state:
        st.session_state.all_hidden = False
    if st.session_state.all_hidden:
        hide_all_classes = st.button("Show All Classes",key="hide_all")
    else:
        hide_all_classes = st.button("Hide All Classes",key="hide_all")
    if st.session_state.all_closed:
        close_all_enroll = st.button("Show All Classes",key="close_all")
    else:
        close_all_enroll = st.button("Hide All Classes",key="close_all")
    if hide_all_classes:
        teaches = load_data(TEACHERS_DB_PATH)
        if st.session_state.all_hidden:
            st.session_state.all_hidden = False
            for info in teaches:
                teaches[info]["is_active"] = True
        else:
            st.session_state.all_hidden = True
            for info in teaches:
                teaches[info]["is_active"] = False
        save_data(TEACHERS_DB_PATH, teaches)
        st.rerun()

    if close_all_enroll:
        teaches = load_data(TEACHERS_DB_PATH)
        if st.session_state.all_closed:
            st.session_state.all_closed = False
            for info in teaches:
                teaches[info]["allow_enroll"] = True
        else:
            st.session_state.all_closed = True
            for info in teaches:
                teaches[info]["allow_enroll"] = False
        save_data(TEACHERS_DB_PATH, teaches)
        st.rerun()

def teacher_login_page():
    # REMOVE THIS BLOCK - Check is now done in the main router
    # if st.session_state.get("teacher_logged_in"):
    #    teacher_dashboard()
    #    st.stop()

    # Use hardcoded English for this page for now
    st.title("Teacher Portal Login")
    entered_id = st.text_input("Enter your Teacher ID:", type="password", key="teacher_id_input")
    if st.button("Login", key="teacher_login_submit"):
        if not entered_id: st.warning("Please enter ID.")
        else:
            teacher_name, teacher_details = validate_teacher_id(entered_id) # Uses validate_teacher_id
            if teacher_name:
                # Set session state
                st.session_state.teacher_logged_in = True
                st.session_state.teacher_id = entered_id
                st.session_state.teacher_name = teacher_name
                st.success(f"Welcome, {teacher_name}!")
                # Rerun will now hit the routing logic which will call teacher_dashboard directly
                st.rerun()
            else: st.error("Invalid Teacher ID.")
# --- Main Application Logic ---
params = st.query_params
plain_id = params.get("id", ""); plain_id = plain_id[0] if isinstance(plain_id, list) else plain_id
if not plain_id: st.error("No user id provided (?id=...)"); st.stop()
request_id = plain_id.lower()

# --- Routing ---
if request_id == "admin":
    _ = admin_route() # Assign return value to _ to potentially suppress output

elif request_id == "teacher":
    if st.session_state.get("teacher_logged_in"):
        _ = teacher_dashboard()  # Assign return value to _
    else:
        _ = teacher_login_page() # Assign return value to _

# --- STUDENT/USER PATH (Using secure_id for Enrollment) ---
else:
    selected_language = st.sidebar.selectbox(texts["English"]["language_label"] + " / " + texts["中文"]["language_label"], options=["English", "中文"], key="lang_select")
    lang = texts.get(selected_language, texts["English"])
    lang_code = 'en' if selected_language == 'English' else 'zh-cn'
    secure_id = request_id # The unique ID for the current user
    st.markdown(f"""<script>document.title = "{lang['page_title']}";</script>""", unsafe_allow_html=True)

    def format_location(location_name):
        if selected_language == "English" or not translator: return location_name
        return translate_dynamic_text(translator, location_name, lang_code)

    # Load necessary data
    user_database = load_data(USER_DB_PATH)
    teachers_database = load_data(TEACHERS_DB_PATH)
    enrollments = load_data(ENROLLMENTS_DB_PATH) # Contains {teacher: [student_id,...]}

    # --- REGISTRATION Section (Unchanged) ---
    if secure_id not in user_database:
        # ... (Registration code remains the same - saves name, grade, raz, location keyed by secure_id) ...
        st.title(lang["page_title"]); st.write(lang["register_prompt"])
        new_user_name = st.text_input(lang["register_name_label"], key="reg_name")
        new_user_grade = st.text_input(lang["register_grade_label"], key="reg_grade")
        new_user_raz = st.text_input(lang["register_raz_label"], key="reg_raz")
        country_options = [lang["select_country"]] + sorted(location_data.keys()); selected_country = st.selectbox(lang["register_country_label"], options=country_options, key="reg_country", index=0, format_func=format_location)
        state_options = [lang["select_state"]];
        if selected_country != lang["select_country"] and selected_country in location_data: state_options.extend(sorted(location_data[selected_country].keys()))
        selected_state = st.selectbox(lang["register_state_label"], options=state_options, key="reg_state", index=0, disabled=(selected_country == lang["select_country"]), format_func=format_location)
        city_options = [lang["select_city"]];
        if selected_state != lang["select_state"] and selected_country in location_data and selected_state in location_data[selected_country]: city_options.extend(sorted(location_data[selected_country][selected_state]))
        selected_city = st.selectbox(lang["register_city_label"], options=city_options, key="reg_city", index=0, disabled=(selected_state == lang["select_state"]), format_func=format_location)
        st.markdown("---")
        if st.button(lang["register_button"], key="register_btn"):
            if new_user_name.strip() and selected_country != lang["select_country"] and selected_state != lang["select_state"] and selected_city != lang["select_city"]:
                user_data_to_save = {"name": new_user_name.strip(),"grade": new_user_grade.strip(),"raz_level": new_user_raz.strip(),"country": selected_country, "state": selected_state, "city": selected_city}
                user_database[secure_id] = user_data_to_save
                save_data(USER_DB_PATH, user_database); user_database_global = user_database
                st.success(lang["registered_success"].format(name=new_user_name.strip())); st.balloons(); time.sleep(1); st.rerun()
            else: st.error(lang["fill_all_fields"])
        st.stop()

    # --- MAIN ENROLLMENT Section ---
    user_info = user_database.get(secure_id) # Get current user's details
    if isinstance(user_info, dict): user_name = user_info.get("name", f"Unknown ({secure_id})") # Display name but use ID internally
    # Handle old format if necessary, though less likely now
    elif isinstance(user_info, str): user_name = f"{user_info} ({secure_id})"
    else: user_name = f"Unknown ({secure_id})"; st.sidebar.error("User data error.")

    # ... (Sidebar display - unchanged) ...
    st.sidebar.write(lang["logged_in"].format(name=user_name)) # Display name
    if isinstance(user_info, dict):
        c, s, ci, gr, rz = user_info.get("country"), user_info.get("state"), user_info.get("city"), user_info.get("grade"), user_info.get("raz_level")
        loc_str = f"{format_location(ci)}, {format_location(s)}, {format_location(c)}" if c and s and ci else ""; details_str = f"Grade: {gr}" if gr else "";
        if rz: details_str += f" | RAZ: {rz}"
        if loc_str: st.sidebar.caption(loc_str);
        if details_str: st.sidebar.caption(details_str)

    st.title(lang["page_title"])
    if st.sidebar.button(lang["refresh"]): st.rerun()

    # --- Teacher Search and Filter (Unchanged) ---
    # ... (Search/Filter logic remains the same) ...
    st.subheader(lang["teacher_search_label"]); col_search, col_grade_filter = st.columns([3, 2])
    with col_search: teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter", label_visibility="collapsed")
    active_teachers = {n: i for n, i in teachers_database.items() if i.get("is_active", True)}
    unique_grades = sorted(list({str(i.get("grade","")).strip() for i in active_teachers.values() if str(i.get("grade","")).strip()}))
    grade_options = [lang["all_grades"]] + unique_grades
    with col_grade_filter: selected_grade_filter = st.selectbox(lang["grade_select_label"], options=grade_options, key="grade_select")
    filtered_teachers = {};
    if active_teachers:
        term = teacher_filter.strip().lower()
        for n, i in active_teachers.items(): name_match = (not term) or (term in n.lower()); grade_match = (selected_grade_filter == lang["all_grades"]) or (str(i.get("grade","")).strip() == selected_grade_filter);
        if name_match and grade_match: filtered_teachers[n] = i
    st.markdown("---")


    # --- Display Teachers (Using secure_id for checks/actions) ---
    if not active_teachers: st.warning(lang["no_teachers_available"])
    elif not filtered_teachers: st.error(lang["teacher_not_found_error"])
    else:

        for teacher_name, teacher_info in filtered_teachers.items():
            st.subheader(teacher_name)
            
    # ... (Class Status display and buttons - unch
            # ... (Display Subject/Grade/Description - unchanged) ...
            subject_en = teacher_info.get("subject_en", "N/A"); display_subject = subject_en
            if selected_language != "English" and translator: display_subject = translate_dynamic_text(translator, subject_en, lang_code)
            grade = teacher_info.get("grade", "N/A"); desc_parts = [];
            if display_subject != "N/A": desc_parts.append(f"**{display_subject}**")
            if grade != "N/A": desc_parts.append(f"({lang['to_grade']} **{grade}**)")
            st.write(f"{lang['teaches']} {' '.join(desc_parts)}" if desc_parts else f"({lang['teaches']} N/A)")
            desc_en = teacher_info.get("description_en", ""); desc_zh = teacher_info.get("description_zh", ""); display_desc = desc_zh if selected_language == "中文" and desc_zh else desc_en
            if display_desc: st.markdown(f"> _{display_desc}_")
            else: st.caption(f"_{lang['no_description_available']}_")
            ratt=teacher_info.get("rating",None)
            if (ratt != None and ratt.isdigit() and int(ratt)>=0):
                st_star_rating(label = lang["class_rating"], maxValue = 5, defaultValue = int(teacher_info.get("rating","0")), key = "rating", read_only = True )
            else:
                st.subheader(lang["class_rating"])
                st.info(lang["class_no_rating"])
            # --- Enrollment status/buttons (Using secure_id) ---
            current_teacher_enrollment_ids = enrollments.get(teacher_name, []) # Get list of IDs
            count = len(current_teacher_enrollment_ids)
            cap = teacher_info.get("enrollment_cap"); cap_text = lang["unlimited"] if cap is None else str(cap)
            is_full = False if cap is None else count >= cap
            all_enr = teacher_info.get("allow_enroll")

            # Check enrollment based on the current user's secure_id
            is_enrolled = secure_id in current_teacher_enrollment_ids

            st.caption(lang["user_enrollment_caption"].format(count=count, cap=cap_text))
            col1, col2 = st.columns(2)

            with col1:
                enroll_label = lang["enroll_button"]
                if is_full:
                    enroll_label = lang["enrollment_full"]
                elif is_enrolled:
                    enroll_label=lang["enroll_button"]
                elif not all_enr:
                    enroll_label = lang["enrollment_closed"]
                enroll_disabled = is_enrolled or is_full or not all_enr
                enroll_clicked = st.button(enroll_label, key=f"enroll_{teacher_name}_{secure_id}", disabled=enroll_disabled, use_container_width=True) # Key uses secure_id
            with col2:
                cancel_clicked = st.button(lang["cancel_button"], key=f"cancel_{teacher_name}_{secure_id}", disabled=not is_enrolled, use_container_width=True) # Key uses secure_id

            # --- Button Actions (Using secure_id) ---
            if enroll_clicked:
                # Re-check conditions on click, use secure_id
                enrollments_now = load_data(ENROLLMENTS_DB_PATH) # Load fresh
                teacher_id_list_now = enrollments_now.get(teacher_name, [])
                teacher_info_now = load_data(TEACHERS_DB_PATH).get(teacher_name, {})
                cap_now = teacher_info_now.get("enrollment_cap")
                is_full_now = False if cap_now is None else len(teacher_id_list_now) >= cap_now

                if secure_id not in teacher_id_list_now and not is_full_now:
                    teacher_id_list_now.append(secure_id) # <-- Add secure_id
                    enrollments_now[teacher_name] = teacher_id_list_now
                    save_data(ENROLLMENTS_DB_PATH, enrollments_now)
                    enrollments_global = enrollments_now # Update global state if needed
                    st.success(lang["enroll_success"].format(name=user_name, teacher=teacher_name))
                    st.rerun()
                # No explicit else needed for already enrolled/full, button is disabled

            if cancel_clicked:
                # Use secure_id for removal
                enrollments_now = load_data(ENROLLMENTS_DB_PATH) # Load fresh
                if teacher_name in enrollments_now and secure_id in enrollments_now[teacher_name]:
                    enrollments_now[teacher_name].remove(secure_id) # <-- Remove secure_id
                    if not enrollments_now[teacher_name]: # Remove teacher key if list empty
                        del enrollments_now[teacher_name]
                    save_data(ENROLLMENTS_DB_PATH, enrollments_now)
                    enrollments_global = enrollments_now # Update global state if needed
                    st.info(lang["enrollment_cancelled"])
                    st.rerun()
                # No explicit else needed, button disabled if not enrolled

            # --- Enrollment List Expander (Display names from IDs) ---
            with st.expander(f"{lang['enrolled_label']} ({count})"):
                if current_teacher_enrollment_ids:
                    # Create list of names to display
                    display_names = []
                    for s_id in current_teacher_enrollment_ids:
                        s_info = user_database.get(s_id) # Use already loaded user_database
                        s_name_display = f"Unknown ID ({s_id})" # Default
                        if isinstance(s_info, dict):
                            s_name_display = s_info.get("name", s_name_display)
                        elif isinstance(s_info, str): # Old format
                            s_name_display = f"{s_info} ({s_id})"

                        # Highlight the current user
                        if s_id == secure_id:
                             s_name_display += f" **({lang['you_marker']})**"
                        display_names.append(s_name_display)

                    # Display sorted names
                    for i, name_to_show in enumerate(sorted(display_names), 1):
                        st.markdown(f"{i}. {name_to_show}")
                else:
                    st.write(lang["no_enrollments"])
            st.markdown("---") # Separator between teachers
