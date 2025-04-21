# Required library: pip install googletrans==4.0.0-rc1 streamlit pandas
# Add googletrans==4.0.0-rc1 and pandas to your requirements.txt

import streamlit as st
import json
import os
import hmac
import hashlib
import pandas as pd
import uuid
import time # Potentially useful for delays with translator
from googletrans import Translator, LANGUAGES # Using googletrans (unofficial)

# --- Translation Setup ---

# !!! IMPORTANT CAVEAT !!!
# googletrans is an UNOFFICIAL library relying on reverse-engineered APIs.
# It can BREAK AT ANY TIME without warning if Google changes its Translate service.
# It's NOT RECOMMENDED for production applications requiring high reliability.
# Consider official APIs (Google Cloud Translation, Azure, DeepL) for production,
# which require setup, API keys, and usually incur costs.
# This implementation also lacks robust error handling for network issues, rate limits etc.

# Initialize translator (consider doing this once)
# Adding user_agent might slightly help reduce blocking issues, but not guaranteed.
try:
    translator = Translator(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
except Exception as e:
    st.error(f"Failed to initialize translator: {e}. Translation features will not work.")
    translator = None # Ensure translator object exists but is None if init fails

# Cache translation results to avoid repeated API calls and hitting limits
@st.cache_data(ttl=3600) # Cache for 1 hour
def translate_text(_translator, text, target_lang_code):
    """Translates text using googletrans with basic error handling and caching."""
    if not _translator:
        # st.warning("Translator not initialized. Cannot translate.")
        return text # Return original if translator failed to init

    if not text or target_lang_code == 'en':
        return text # Return original if empty or target is English

    # Map Streamlit language name to googletrans code if needed
    if target_lang_code == 'zh': # Assuming '中文' maps to simplified chinese
        target_lang_code = 'zh-cn'

    if target_lang_code not in LANGUAGES and target_lang_code not in ['zh-cn', 'zh-tw']:
         # st.warning(f"Unsupported language code for translation: {target_lang_code}")
         return text # Return original if language not supported

    try:
        # Optional: Add a small delay? time.sleep(0.05)
        translated = _translator.translate(text, dest=target_lang_code)
        return translated.text
    except Exception as e:
        # Avoid flooding the UI with errors, maybe log instead
        print(f"WARN: Translation Error for '{text}' to {target_lang_code}: {e}. Returning original.")
        # st.warning(f"Translation Error: {e}. Returning original text.")
        return text

# Helper to get the language dictionary (either base English or translated)
@st.cache_data(ttl=3600)
def get_language_dict(_translator, base_texts_dict, target_language):
    """Returns the base dict if English, or a translated dict."""
    if target_language == "English" or not _translator:
        return base_texts_dict # Return base if English or translator failed
    else:
        # Assume target_language == "中文", map to 'zh-cn' code for translator
        lang_code = 'zh-cn'
        translated_dict = {}
        for key, value in base_texts_dict.items():
            # Translate each value in the base dictionary
            translated_dict[key] = translate_text(_translator, value, lang_code)
        return translated_dict

# --- End Translation Setup ---

# --- Configuration ---
st.markdown("""<style>.st-emotion-cache-1p1m4ay{ visibility:hidden }</style>""", unsafe_allow_html=True)
USER_DB_PATH = "user_db.json"
ENROLLMENTS_DB_PATH = "enrollments.json"
TEACHERS_DB_PATH = "teachers.json"

# --- Simplified Base Texts (English Only) ---
# All UI text elements will be translated from this base dictionary.
base_texts = {
    "page_title": "PLE Youth Enrollment",
    "language_label": "Choose Language",
    "teacher_search_label": "Search for a teacher by name:",
    "teacher_not_found_error": "No active teacher found with that search term.",
    "enter_teacher_info": "Displaying all available teachers. Use the search box above to filter.",
    "teaches": "Teaches",
    "to_grade": "grade",
    "enroll_button": "Enroll",
    "cancel_button": "Cancel Enrollment",
    "enroll_success": "Thank you, {name}! You are now enrolled in {teacher}'s class!",
    "enrollment_cancelled": "Enrollment has been cancelled.",
    "register_prompt": "Welcome! Please register by entering the student's details below:",
    "register_button": "Register",
    "logged_in": "Logged in as: {name}",
    "enrolled_label": "Enrolled Students",
    "no_enrollments": "No students enrolled yet.",
    "not_enrolled": "Your name was not found in the enrollment.",
    "name_required": "Please enter your name to register.",
    "no_teachers_available": "No teachers are currently available for enrollment.",
    "enrollment_full": "Enrollment Full",
    "user_enrollment_caption": "Enrolled: {count} / {cap}",
    "unlimited": "Unlimited",
    "grade_select_label": "Select Grade",
    "all_grades": "All",
    "refresh": "refresh",
    "register_name_label": "Student's English Full Name",
    "register_grade_label": "Current Grade",
    "register_country_label": "Country",
    "register_state_label": "State/Province",
    "register_city_label": "City",
    "select_country": "--- Select Country ---",
    "select_state": "--- Select State/Province ---",
    "select_city": "--- Select City ---",
    "fill_all_fields": "Please fill in Name and select a valid Country, State/Province, and City.",
    "already_enrolled_warning": "Already enrolled.",
    "registered_success": "Registered {name}! Reloading page.",
    "save_settings_button": "Save Settings",
    "settings_updated_success": "Settings updated successfully!",
    "class_info_header": "Class Information",
    "subject_en_label": "Subject (English)", # Kept for clarity, maybe Admin/Teacher needs it
    "grade_label": "Grade",
    "enrollment_limit_header": "Enrollment Limit",
    "max_students_label": "Maximum Students (leave blank or 0 for unlimited)",
    "class_status_header": "Class Status",
    "status_active": "Active (Students can enroll)",
    "status_cancelled": "Cancelled (Students cannot enroll)",
    "cancel_class_button": "Cancel Class (Hide from Enrollment)",
    "reactivate_class_button": "Reactivate Class (Allow Enrollment)",
    "enrollment_overview_header": "Enrollment Overview",
    "current_enrollment_metric": "Current Enrollment",
    "enrolled_students_list_header": "Enrolled Students:",
    "teacher_dashboard_title": "Teacher Dashboard: {name}",
    "teacher_logout_button": "Logout",
    "teacher_login_title": "Teacher Portal Login",
    "teacher_id_prompt": "Enter your Teacher ID:",
    "login_button": "Login",
    "invalid_teacher_id_error": "Invalid Teacher ID.",
    "admin_dashboard_title": "Admin Dashboard",
    "admin_password_prompt": "Enter Admin Password:",
    "admin_access_granted": "Access granted.",
    "refresh_data_button": "Refresh Data from Files",
    "manage_teachers_header": "Manage Teachers",
    "manage_teachers_info": "Add/edit details. Set cap=0 or leave blank for unlimited. Use trash icon to remove.",
    "save_teachers_button": "Save Changes to Teachers",
    "manage_students_header": "Manage Registered Students",
    "save_students_button": "Save Changes to Students",
    "manage_assignments_header": "Teacher-Student Assignments",
    "save_assignments_button": "Save Changes to Assignments",
    # Add any other static text keys used in Admin/Teacher panels here
}


# --- Simplified Location Data (English Only) ---
# Store only English names. These will be translated for display using format_func.
location_data = {
    "USA": {
        "California": ["Los Angeles", "San Francisco", "San Diego", "Sacramento"],
        "New York": ["New York City", "Buffalo", "Rochester", "Albany"],
        "Texas": ["Houston", "Dallas", "Austin", "San Antonio"]
    },
    "China": {
        "Beijing Municipality": ["Beijing"],
        "Shanghai Municipality": ["Shanghai"],
        "Guangdong Province": ["Guangzhou", "Shenzhen", "Dongguan"],
        "Zhejiang Province": ["Hangzhou", "Ningbo", "Wenzhou"]
    },
    "Canada": {
        "Ontario": ["Toronto", "Ottawa", "Mississauga", "Hamilton"],
        "Quebec": ["Montreal", "Quebec City", "Laval", "Gatineau"],
        "British Columbia": ["Vancouver", "Surrey", "Burnaby", "Richmond"]
    },
    "India": {
        "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
        "Delhi": ["New Delhi"],
        "Karnataka": ["Bangalore", "Mysore", "Hubli"]
    }
    # Add more countries/states/cities with English names
}

# --- File Database Helper Functions ---
def load_data(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                content = f.read()
                if not content: return {}
                return json.loads(content)
            except json.JSONDecodeError:
                st.error(f"Error decoding JSON from {path}.")
                return {}
    return {}

def save_data(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: st.error(f"Error saving data to {path}: {e}")

# --- Load file databases ---
user_database = load_data(USER_DB_PATH)
enrollments = load_data(ENROLLMENTS_DB_PATH)
teachers_database = load_data(TEACHERS_DB_PATH)

# --- Encryption & ID Generation ---
if "secret_key" not in st.secrets: st.error("`secret_key` missing in Streamlit secrets."); st.stop()
SECRET_KEY = st.secrets["secret_key"]
def encrypt_id(plain_id: str) -> str: return hmac.new(SECRET_KEY.encode(), plain_id.encode(), hashlib.sha256).hexdigest()
def generate_teacher_id(): return uuid.uuid4().hex

# --- Validate Teacher ID ---
def validate_teacher_id(entered_id: str):
    # Reload fresh data in case admin made changes
    current_teachers_db = load_data(TEACHERS_DB_PATH)
    for name, details in current_teachers_db.items():
        if details.get("id") == entered_id: return name, details
    return None, None

# --- Teacher Dashboard (Simplified - English Only Data Handling) ---
# NOTE: This dashboard currently doesn't translate its own UI elements.
# It would require passing the 'lang' dictionary or using session state
# if dynamic translation of the dashboard itself is needed.
def teacher_dashboard():
    global teachers_database, enrollments # Allow modification
    # Use hardcoded English for dashboard elements for now
    st.title(f"Teacher Dashboard: {st.session_state.teacher_name}")
    if st.button("Logout", key="teacher_logout"):
        del st.session_state.teacher_logged_in, st.session_state.teacher_id, st.session_state.teacher_name
        st.success("Logged out."); st.rerun()
    if st.button("Refresh"):
        st.rerun()
    st.markdown("---")

    teacher_name = st.session_state.teacher_name
    # Reload data for freshness
    current_teachers_db = load_data(TEACHERS_DB_PATH)
    teacher_details = current_teachers_db.get(teacher_name)
    if not teacher_details: st.error("Teacher data not found."); st.stop()

    st.subheader("Manage Class Settings")
    with st.form("edit_teacher_form"):
        st.write("**Class Information**")
        # Only English subject is managed now
        new_subject_en = st.text_input("Subject (English)", value=teacher_details.get("subject_en", ""))
        # Removed subject_zh input
        new_grade = st.text_input("Grade", value=teacher_details.get("grade", ""))
        st.write("**Enrollment Limit**")
        current_cap = teacher_details.get("enrollment_cap")
        new_cap = st.number_input("Maximum Students (leave blank or 0 for unlimited)", min_value=0, value=current_cap if current_cap is not None else None, step=1, format="%d", key="teacher_edit_cap")
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            processed_cap = int(new_cap) if new_cap is not None and new_cap > 0 else None
            current_teachers_db[teacher_name].update({
                "subject_en": new_subject_en.strip(),
                # Removed subject_zh update
                "grade": new_grade.strip(),
                "enrollment_cap": processed_cap
            })
            save_data(TEACHERS_DB_PATH, current_teachers_db)
            teachers_database = current_teachers_db # Update global state
            st.success("Settings updated successfully!")
            st.rerun()

    st.markdown("---")
    st.subheader("Class Status")
    is_active = teacher_details.get("is_active", True)
    status_text = "Active (Students can enroll)" if is_active else "Cancelled (Students cannot enroll)"
    status_func = st.success if is_active else st.warning
    status_func(f"Status: {status_text}")
    if is_active:
        if st.button("Cancel Class (Hide from Enrollment)", key="cancel_class_btn"):
            current_teachers_db[teacher_name]["is_active"] = False
            save_data(TEACHERS_DB_PATH, current_teachers_db); teachers_database = current_teachers_db
            st.warning("Class cancelled."); st.rerun()
    else:
        if st.button("Reactivate Class (Allow Enrollment)", key="reactivate_class_btn"):
            current_teachers_db[teacher_name]["is_active"] = True
            save_data(TEACHERS_DB_PATH, current_teachers_db); teachers_database = current_teachers_db
            st.success("Class reactivated."); st.rerun()

    st.markdown("---")
    st.subheader("Enrollment Overview")
    # Reload enrollments
    current_enrollments = load_data(ENROLLMENTS_DB_PATH)
    enrolled_students = current_enrollments.get(teacher_name, [])
    enrollment_count = len(enrolled_students)
    display_cap = teacher_details.get("enrollment_cap", "Unlimited")
    if isinstance(display_cap, int) and display_cap <= 0: display_cap = "Unlimited"
    st.metric("Current Enrollment", f"{enrollment_count} / {display_cap}")
    if enrolled_students:
        st.write("**Enrolled Students:**")
        for i, student_name in enumerate(enrolled_students, 1):
             st.markdown(f"{i}. {student_name}") # Names are not translated
    else:
        st.info("No students are currently enrolled.")

# --- Teacher Login Page ---
def teacher_login_page():
    if st.session_state.get("teacher_logged_in"): teacher_dashboard(); st.stop()
    # Use hardcoded English for this page for now
    st.title("Teacher Portal Login")
    entered_id = st.text_input("Enter your Teacher ID:", type="password", key="teacher_id_input")
    if st.button("Login", key="teacher_login_submit"):
        if not entered_id: st.warning("Please enter ID.")
        else:
            teacher_name, teacher_details = validate_teacher_id(entered_id)
            if teacher_name and teacher_details:
                st.session_state.teacher_logged_in = True
                st.session_state.teacher_id = entered_id
                st.session_state.teacher_name = teacher_name
                st.success(f"Welcome, {teacher_name}!"); st.rerun()
            else: st.error("Invalid Teacher ID.")

# --- Admin Route (Simplified - English Only Data Handling) ---
def admin_route():
    global user_database, enrollments, teachers_database # Allow modification
    # Use hardcoded English for Admin panel UI
    st.title("Admin Dashboard")
    if "passcode" not in st.secrets: st.error("Admin `passcode` missing in Streamlit secrets."); st.stop()
    admin_password = st.text_input("Enter Admin Password:", type="password", key="admin_pw")
    if not admin_password: st.warning("Please enter password."); st.stop()
    if admin_password != st.secrets["passcode"]: st.error("Incorrect password."); st.stop()
    st.success("Access granted.")
    if st.button("Refresh Data from Files"):
        user_database, enrollments, teachers_database = map(load_data, [USER_DB_PATH, ENROLLMENTS_DB_PATH, TEACHERS_DB_PATH])
        st.rerun()
    st.markdown("---")

    # --- Manage Teachers ---
    st.subheader("Manage Teachers")
    st.markdown("Add/edit details. Set cap=0 or leave blank for unlimited. Use trash icon to remove.")
    teachers_list = []
    needs_saving_defaults = False
    temp_teachers_db = load_data(TEACHERS_DB_PATH) # Load fresh data
    for name, details in temp_teachers_db.items():
        if "id" not in details: details["id"] = generate_teacher_id(); needs_saving_defaults = True
        if "is_active" not in details: details["is_active"] = True; needs_saving_defaults = True
        if "enrollment_cap" not in details: details["enrollment_cap"] = None; needs_saving_defaults = True
        teachers_list.append({
            "Teacher ID": details["id"],
            "Teacher Name": name,
            "Subject (English)": details.get("subject_en", ""), # Only English subject
            # Removed Subject (Chinese)
            "Grade": details.get("grade", ""),
            "Is Active": details.get("is_active"),
            "Enrollment Cap": details.get("enrollment_cap")
        })
    if needs_saving_defaults:
        save_data(TEACHERS_DB_PATH, temp_teachers_db)
        teachers_database = temp_teachers_db # Update global state
        st.info("Applied default values (ID/Status/Cap) where missing. Data saved.")

    if not teachers_list:
        teachers_df = pd.DataFrame(columns=["Teacher ID", "Teacher Name", "Subject (English)", "Grade", "Is Active", "Enrollment Cap"])
    else:
        teachers_df = pd.DataFrame(teachers_list)

    edited_teachers_df = st.data_editor(
        teachers_df,
        num_rows="dynamic",
        key="teacher_editor",
        column_config={
             "Teacher ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
             "Teacher Name": st.column_config.TextColumn("Name", required=True),
             "Subject (English)": st.column_config.TextColumn("Subject EN"), # English only
             # Removed Subject ZH config
             "Grade": st.column_config.TextColumn("Grade", width="small"),
             "Is Active": st.column_config.CheckboxColumn("Active?", disabled=True, width="small"), # Status managed in Teacher dash
             "Enrollment Cap": st.column_config.NumberColumn("Cap", help="Max students. Leave blank or 0 for unlimited.", min_value=0, step=1, format="%d", width="small")
        },
        # Removed Subject (Chinese) from order
        column_order=("Teacher ID", "Teacher Name", "Enrollment Cap", "Subject (English)", "Grade", "Is Active"),
        use_container_width=True
    )

    if st.button("Save Changes to Teachers"):
        original_teachers_data = teachers_database.copy() # Use current global state
        new_teachers_database = {}
        error_occurred = False; seen_names = set(); processed_ids = set()
        for index, row in edited_teachers_df.iterrows():
            name = row["Teacher Name"]
            teacher_id = row["Teacher ID"]
            enrollment_cap_input = row["Enrollment Cap"]
            # --- ID Handling ---
            is_new_teacher = pd.isna(teacher_id) or str(teacher_id).strip() == ""
            if is_new_teacher:
                teacher_id = generate_teacher_id()
            # --- Validation ---
            if pd.isna(name) or str(name).strip() == "": st.error(f"Row {index+1}: Name empty."); error_occurred = True; continue
            name = str(name).strip()
            if name in seen_names: st.error(f"Row {index+1}: Duplicate Name '{name}'."); error_occurred = True; continue
            # Check if name exists with a *different* ID
            for existing_name, existing_details in original_teachers_data.items():
                 if existing_details.get("id") != teacher_id and existing_name == name:
                     st.error(f"Row {index+1}: Name '{name}' already used by another teacher ID."); error_occurred = True; break
            if error_occurred: continue # Skip if name conflict found
            seen_names.add(name)
            processed_ids.add(teacher_id)
            # --- Process Cap ---
            processed_cap = None
            if pd.notna(enrollment_cap_input) and enrollment_cap_input > 0:
                 try: processed_cap = int(enrollment_cap_input)
                 except (ValueError, TypeError): st.error(f"Row {index+1}: Invalid Cap '{enrollment_cap_input}'."); error_occurred = True; continue
            # --- Preserve Active Status (managed by teacher) ---
            original_details = next((d for _, d in original_teachers_data.items() if d.get("id") == teacher_id), None)
            current_is_active = original_details.get("is_active", True) if original_details else True
            # --- Build new entry ---
            new_teachers_database[name] = {
                "id": teacher_id,
                "subject_en": str(row["Subject (English)"]) if pd.notna(row["Subject (English)"]) else "", # Only English subject
                # Removed subject_zh
                "grade": str(row["Grade"]) if pd.notna(row["Grade"]) else "",
                "is_active": current_is_active,
                "enrollment_cap": processed_cap
            }
        # --- Handle Deletions ---
        deleted_teacher_names = [on for on, od in original_teachers_data.items() if od.get("id") not in processed_ids]
        # --- Save if no errors ---
        if not error_occurred:
            try:
                save_data(TEACHERS_DB_PATH, new_teachers_database)
                teachers_database = new_teachers_database # Update global state
                st.success("Teacher data updated!")
                # Handle enrollments for deleted teachers
                if deleted_teacher_names:
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
                         enrollments = new_enrollments_after_teacher_delete # Update global state
                st.rerun()
            except Exception as e: st.error(f"Failed to save teacher data: {e}")
        else: st.warning("Fix errors before saving teacher changes.")

    st.markdown("---")
    # --- Manage Registered Students ---
    st.subheader("Manage Registered Students")
    students_list = []
    temp_user_db = load_data(USER_DB_PATH) # Load fresh data
    for user_id, user_info in temp_user_db.items():
         # New structure assumed: dict with 'name', 'grade', 'country', 'state', 'city' (all English)
        if isinstance(user_info, dict):
            students_list.append({
                "Encrypted ID": user_id,
                "Name": user_info.get("name", ""),
                "Grade": user_info.get("grade", ""),
                "Country": user_info.get("country", ""), # English name/key
                "State/Province": user_info.get("state", ""), # English name/key
                "City": user_info.get("city", "") # English name/key
            })
        elif isinstance(user_info, str): # Handle old format (just name)
             students_list.append({"Encrypted ID": user_id, "Name": user_info, "Grade": "", "Country": "", "State/Province": "", "City": ""})
        # Else: ignore unexpected formats

    if not students_list:
        students_df = pd.DataFrame(columns=["Encrypted ID", "Name", "Grade", "Country", "State/Province", "City"])
    else:
        students_df = pd.DataFrame(students_list)

    edited_students_df = st.data_editor(
        students_df,
        num_rows="dynamic",
        key="student_editor",
        column_config={
            "Encrypted ID": st.column_config.TextColumn("Encrypted ID", disabled=True),
            "Name": st.column_config.TextColumn("Student Name", required=True), # Names not translated
            "Grade": st.column_config.TextColumn("Grade"),
            "Country": st.column_config.TextColumn("Country"), # Display English key
            "State/Province": st.column_config.TextColumn("State/Province"), # Display English key
            "City": st.column_config.TextColumn("City") # Display English key
        },
        use_container_width=True
    )

    if st.button("Save Changes to Students"):
        original_ids = set(students_df["Encrypted ID"])
        edited_ids = set(edited_students_df["Encrypted ID"])
        deleted_ids = original_ids - edited_ids
        # Get names of deleted students *before* updating database
        user_db_before_del = temp_user_db # Use the freshly loaded data
        deleted_student_names = set()
        for user_id in deleted_ids:
            user_info = user_db_before_del.get(user_id)
            if isinstance(user_info, str): deleted_student_names.add(user_info)
            elif isinstance(user_info, dict): deleted_student_names.add(user_info.get("name", ""))

        new_user_database = {}
        error_occurred = False
        name_changes = {}  # old_name -> new_name

        for index, row in edited_students_df.iterrows():
            user_id = row["Encrypted ID"]
            name = row["Name"]
            grade = row["Grade"]
            country = row["Country"] # Expecting English key
            state = row["State/Province"] # Expecting English key
            city = row["City"] # Expecting English key
            # --- Validation ---
            if pd.isna(name) or str(name).strip() == "": st.error(f"Row {index+1}: Name empty."); error_occurred = True; continue
            if pd.isna(user_id): st.error(f"Row {index+1}: ID missing (should not happen)."); error_occurred = True; continue
            # --- Clean data ---
            clean_name = str(name).strip()
            clean_grade = str(grade).strip() if pd.notna(grade) else ""
            clean_country = str(country).strip() if pd.notna(country) else ""
            clean_state = str(state).strip() if pd.notna(state) else ""
            clean_city = str(city).strip() if pd.notna(city) else ""
            # --- Build entry ---
            new_user_database[user_id] = {
                "name": clean_name,
                "grade": clean_grade,
                "country": clean_country, # Save English key
                "state": clean_state, # Save English key
                "city": clean_city # Save English key
            }
            # --- Check for name change ---
            old_user_info = user_db_before_del.get(user_id)
            if old_user_info:
                old_name = old_user_info if isinstance(old_user_info, str) else old_user_info.get("name", "")
                if old_name and old_name != clean_name:
                    name_changes[old_name] = clean_name
        # --- Save if no errors ---
        if not error_occurred:
            try:
                save_data(USER_DB_PATH, new_user_database)
                user_database = new_user_database # Update global state
                st.success("Student data updated!")
                if deleted_student_names: st.info(f"Removed students: {', '.join(filter(None, deleted_student_names))}")

                # --- Update enrollments for deleted students and name changes ---
                current_enrollments = load_data(ENROLLMENTS_DB_PATH)
                new_enrollments = current_enrollments.copy()
                enrollments_updated = False
                # Handle deletions
                for teacher, studs in current_enrollments.items():
                    # Filter out deleted names (ensure deleted_student_names contains non-empty strings)
                    valid_deleted_names = {s for s in deleted_student_names if s}
                    original_length = len(studs)
                    cleaned_list = [s for s in studs if s not in valid_deleted_names]
                    if len(cleaned_list) != original_length:
                        enrollments_updated = True
                        if cleaned_list: new_enrollments[teacher] = cleaned_list
                        # Remove teacher key if list becomes empty after filtering
                        elif teacher in new_enrollments: del new_enrollments[teacher]
                # Handle name changes
                if name_changes:
                    for teacher, studs in new_enrollments.items(): # Iterate over potentially modified dict
                        # Only update if there was a change
                        new_studs = [name_changes.get(s, s) for s in studs]
                        if new_studs != studs:
                            new_enrollments[teacher] = new_studs
                            enrollments_updated = True
                # Save enrollments if updated
                if enrollments_updated:
                    save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                    enrollments = new_enrollments # Update global state
                    st.info("Updated enrollments for deleted students or name changes.")
                st.rerun()
            except Exception as e: st.error(f"Failed to save student data: {e}")
        else: st.warning("Fix errors before saving student changes.")

    st.markdown("---")
    # --- Manage Teacher-Student Assignments ---
    st.subheader("Teacher-Student Assignments")
    assignments = []
    current_enrollments = load_data(ENROLLMENTS_DB_PATH) # Load fresh
    for teacher, students in current_enrollments.items():
        for student in students:
            assignments.append({"Teacher": teacher, "Student": student})

    if not assignments:
        assignments_df = pd.DataFrame(columns=["Teacher", "Student"])
    else:
        assignments_df = pd.DataFrame(assignments)

    # Get available options from current state of other databases
    available_teachers = sorted(list(load_data(TEACHERS_DB_PATH).keys()))
    user_db_for_options = load_data(USER_DB_PATH)
    available_students = sorted([
        (u["name"] if isinstance(u, dict) else u) # Handle both formats
        for u in user_db_for_options.values() if (isinstance(u, dict) and u.get("name")) or isinstance(u, str)
    ])

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

    if st.button("Save Changes to Assignments"):
        new_enrollments = {}
        error_occurred = False
        processed_pairs = set()
        for index, row in edited_assignments.iterrows():
            teacher, student = row["Teacher"], row["Student"]
            # --- Validation ---
            if pd.isna(teacher) or str(teacher).strip() == "": st.error(f"Row {index+1}: Teacher empty."); error_occurred = True; continue
            if pd.isna(student) or str(student).strip() == "": st.error(f"Row {index+1}: Student empty."); error_occurred = True; continue
            teacher, student = str(teacher).strip(), str(student).strip()
            # Check for duplicates in the *edited* data
            if (teacher, student) in processed_pairs:
                st.warning(f"Row {index+1}: Duplicate assignment {student} to {teacher} ignored.")
                continue
            processed_pairs.add((teacher, student))
            # --- Check against actual data ---
            if teacher not in available_teachers: st.error(f"Row {index+1}: Invalid teacher '{teacher}'."); error_occurred = True; continue
            if student not in available_students: st.error(f"Row {index+1}: Invalid student '{student}'."); error_occurred = True; continue
            # --- Build new enrollments structure ---
            if teacher not in new_enrollments: new_enrollments[teacher] = []
            # Avoid duplicates within a teacher's list in the new data
            if student not in new_enrollments[teacher]:
                 new_enrollments[teacher].append(student)

        if not error_occurred:
            try:
                # Sort student lists within the new enrollments for consistency
                for teacher in new_enrollments:
                    new_enrollments[teacher].sort()
                save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                enrollments = new_enrollments # Update global state
                st.success("Assignments updated!")
                st.rerun()
            except Exception as e: st.error(f"Failed to save assignments: {e}")
        else: st.warning("Fix errors before saving assignments.")


# --- Main Application Logic ---
params = st.query_params
plain_id = params.get("id", "")
if isinstance(plain_id, list): plain_id = plain_id[0] if plain_id else ""
if not plain_id:
    st.error("No user id provided. Use ?id=your_id, ?id=admin, or ?id=teacher")
    st.stop()

request_id = plain_id.lower()

# --- Routing ---
if request_id == "admin":
    admin_route()
elif request_id == "teacher":
    teacher_login_page()
else:
    # --- STUDENT/USER PATH ---
    selected_language = st.sidebar.selectbox(
        "Language / 语言", # Label itself is static
        options=["English", "中文"],
        key="lang_select",
    )

    # --- Get the appropriate language dictionary (English or Translated) ---
    # Pass the global translator object and base_texts dictionary
    lang = get_language_dict(translator, base_texts, selected_language)
    # Determine language code for dynamic translations ('en' or 'zh-cn')
    lang_code = 'en' if selected_language == 'English' else 'zh-cn'

    secure_id = request_id # Use the raw ID from URL param as the key
    # Use translated page title, with fallback
    st.markdown(f"""<script>document.title = "{lang.get('page_title', 'Enrollment')}";</script>""", unsafe_allow_html=True)

    # --- Reload data for user path ---
    user_database = load_data(USER_DB_PATH)
    teachers_database = load_data(TEACHERS_DB_PATH)
    enrollments = load_data(ENROLLMENTS_DB_PATH)

    # --- REGISTRATION Section ---
    if secure_id not in user_database:
        st.title(lang.get("page_title")) # Use translated title
        st.write(lang.get("register_prompt")) # Use translated prompt

        new_user_name = st.text_input(lang.get("register_name_label"), key="register_input")
        new_user_grade = st.text_input(lang.get("register_grade_label"), key="register_grade")

        # --- Location Dropdowns with format_func for translation ---

        # Helper format function for selectboxes
        def format_location(location_name):
            # Translate only if needed and translator is available
            if selected_language != "English" and translator:
                return translate_text(translator, location_name, lang_code)
            return location_name # Return original English name otherwise

        # Country
        country_label = lang.get("register_country_label")
        select_country_prompt = lang.get("select_country") # Translated prompt
        # Sort keys for consistent order
        country_options = [select_country_prompt] + sorted(list(location_data.keys()))
        selected_country = st.selectbox(
            country_label,
            options=country_options,
            key="register_country", # Stores the English key ('USA', 'China')
            index=0,
            format_func=format_location # Translate for display only
        )

        # State/Province
        state_label = lang.get("register_state_label")
        select_state_prompt = lang.get("select_state") # Translated prompt
        state_options = [select_state_prompt]
        # Populate based on selected English country key
        if selected_country != select_country_prompt and selected_country in location_data:
            # Sort keys for consistent order
            state_options.extend(sorted(list(location_data[selected_country].keys())))
        selected_state = st.selectbox(
            state_label,
            options=state_options,
            key="register_state", # Stores the English key ('California', 'Beijing Municipality')
            index=0,
            disabled=(selected_country == select_country_prompt),
            format_func=format_location # Translate for display only
        )

        # City
        city_label = lang.get("register_city_label")
        select_city_prompt = lang.get("select_city") # Translated prompt
        city_options = [select_city_prompt]
        # Populate based on selected English state key
        if selected_state != select_state_prompt and \
           selected_country in location_data and \
           selected_state in location_data[selected_country]:
            # Sort list for consistent order
            city_options.extend(sorted(location_data[selected_country][selected_state]))
        selected_city = st.selectbox(
            city_label,
            options=city_options,
            key="register_city", # Stores the English name ('Los Angeles', 'Beijing')
            index=0,
            disabled=(selected_state == select_state_prompt),
            format_func=format_location # Translate for display only
        )

        st.markdown("---")

        if st.button(lang.get("register_button"), key="register_btn"):
            # Validate selections are not the prompts and name is entered
            if new_user_name and new_user_name.strip() and \
               selected_country != select_country_prompt and \
               selected_state != select_state_prompt and \
               selected_city != select_city_prompt:

                clean_name = new_user_name.strip()
                clean_grade = new_user_grade.strip() if new_user_grade else ""

                # Save English names/keys directly
                user_data_to_save = {
                    "name": clean_name,
                    "grade": clean_grade,
                    "country": selected_country, # Saved English key
                    "state": selected_state,     # Saved English key
                    "city": selected_city        # Saved English key
                }
                user_database[secure_id] = user_data_to_save
                save_data(USER_DB_PATH, user_database) # Save updated data

                # Use translated success message format string
                success_format = lang.get("registered_success", "Registered {name}! Reloading page.")
                st.success(success_format.format(name=clean_name))
                st.balloons()
                st.rerun()
            else:
                st.error(lang.get("fill_all_fields")) # Use translated error
        st.stop() # Stop execution if user needs to register

    # --- MAIN ENROLLMENT Section (If user is registered) ---
    user_info = user_database.get(secure_id)
    # --- Retrieve user name (assuming new structure with English keys) ---
    if isinstance(user_info, dict):
        user_name = user_info.get("name", "Unknown User")
        # Example: Display location in sidebar (optional)
        country_en = user_info.get("country")
        state_en = user_info.get("state")
        city_en = user_info.get("city")
        if city_en and state_en and country_en and translator: # Check if data exists and translator works
            # Translate parts for display
            loc_disp = f"{format_location(city_en)}, {format_location(state_en)}, {format_location(country_en)}"
            st.sidebar.caption(loc_disp)

    elif isinstance(user_info, str): # Handle old format
        user_name = user_info
    else: # Fallback
        user_name = "Unknown User"
        # Avoid trying to display location if user_info is bad
        st.sidebar.warning("Could not load user details.")


    # Use translated login message
    st.sidebar.write(lang.get("logged_in", "Logged in as: {name}").format(name=user_name))
    st.title(lang.get("page_title")) # Use translated title
    if st.sidebar.button(lang.get("refresh", "Refresh")):
        st.rerun()

    # --- Teacher Search and Filter ---
    st.subheader(lang.get("teacher_search_label")) # Use translated label
    col_search, col_grade_filter = st.columns([3, 2])

    with col_search:
        teacher_filter = st.text_input(
            lang.get("teacher_search_label"),
            key="teacher_filter",
            label_visibility="collapsed"
        )

    # --- Grade Filter ---
    active_teachers = {n: i for n, i in teachers_database.items() if i.get("is_active", True)}
    unique_grades = set() # Use a set to avoid duplicates initially
    if active_teachers:
         for teacher_info in active_teachers.values():
              grade_val = str(teacher_info.get("grade","")).strip()
              if grade_val: # Add non-empty grades
                   unique_grades.add(grade_val)

    # Sort the unique grades
    sorted_unique_grades = sorted(list(unique_grades))

    # Grade options (translate "All" if needed)
    # NOTE: Grade values themselves (like "5", "10") are usually not translated.
    # If you have word-based grades ("Kindergarten"), you'd need translation logic here.
    all_grades_text = lang.get("all_grades", "All")
    grade_options = [all_grades_text] + sorted_unique_grades

    with col_grade_filter:
        selected_grade_display = st.selectbox(
            lang.get("grade_select_label"), # Translated label
            options=grade_options,
            key="grade_select"
            # format_func could be used here if grades themselves needed translation
        )

        # Determine the actual filter value (might be 'All' or a specific grade number/word)
        selected_grade_filter = selected_grade_display
        # No mapping needed if "All" wasn't translated significantly or grade values are numeric


    # --- Filtering Logic ---
    filtered_teachers = {}
    if active_teachers:
        filter_term = teacher_filter.strip().lower()
        for n, i in active_teachers.items():
            # Filter by teacher name (case-insensitive) - Names aren't translated
            name_match = (not filter_term) or (filter_term in n.lower())
            # Filter by grade
            teacher_grade = str(i.get("grade", "")).strip()
            grade_match = (selected_grade_filter == all_grades_text) or \
                          (teacher_grade == selected_grade_filter)

            if name_match and grade_match:
                filtered_teachers[n] = i

    st.markdown("---")

    # --- Display Teachers ---
    if not active_teachers:
        st.warning(lang.get("no_teachers_available")) # Translated warning
    elif not filtered_teachers:
        st.error(lang.get("teacher_not_found_error")) # Translated error
    else:
        # Optionally show info text if no filters applied
        # if not teacher_filter.strip() and selected_grade_filter == all_grades_text:
        #    st.info(lang.get("enter_teacher_info"))

        for teacher_name, teacher_info in filtered_teachers.items():
            st.subheader(teacher_name) # Teacher name not translated

            # --- Translate Subject Dynamically ---
            subject_en = teacher_info.get("subject_en", "N/A") # Get English subject
            display_subject = subject_en # Default to English
            if selected_language != "English" and translator:
                display_subject = translate_text(translator, subject_en, lang_code)

            grade = teacher_info.get("grade", "N/A") # Grade likely not translated

            # Use translated description parts
            description_parts = []
            if display_subject and display_subject != "N/A":
                 description_parts.append(f"**{display_subject}**")
            if grade and grade != "N/A":
                 # Translate the word "grade" using the lang dictionary
                 grade_word = lang.get('to_grade', 'grade')
                 description_parts.append(f"({grade_word} **{grade}**)")

            # Use translated "Teaches" word
            teaches_word = lang.get('teaches', 'Teaches')
            if description_parts:
                st.write(f"{teaches_word} {' '.join(description_parts)}")
            else:
                st.write(f"({teaches_word} N/A)") # Fallback

            # --- Enrollment status and buttons (use translated texts) ---
            current_enrollment_count = len(enrollments.get(teacher_name, []))
            cap = teacher_info.get("enrollment_cap")
            unlimited_text = lang.get("unlimited", "Unlimited") # Translated "Unlimited"
            cap_display = unlimited_text if (cap is None or not isinstance(cap, int) or cap <= 0) else str(cap)
            is_full = False if cap_display == unlimited_text else current_enrollment_count >= cap

            # Use translated caption format string
            caption_format = lang.get("user_enrollment_caption", "Enrolled: {count} / {cap}")
            caption = caption_format.format(count=current_enrollment_count, cap=cap_display)
            st.caption(caption)

            col1, col2 = st.columns(2)
            is_enrolled = user_name in enrollments.get(teacher_name, []) # User name not translated

            with col1:
                enroll_disabled = is_enrolled or is_full
                # Use translated button labels
                enroll_label = lang.get("enroll_button", "Enroll")
                if is_full and not is_enrolled:
                    enroll_label = lang.get("enrollment_full", "Enrollment Full")

                enroll_clicked = st.button(
                    enroll_label,
                    key=f"enroll_button_{teacher_name}_{secure_id}", # Unique key
                    disabled=enroll_disabled,
                    use_container_width=True
                )

            with col2:
                cancel_clicked = st.button(
                    lang.get("cancel_button", "Cancel Enrollment"), # Translated label
                    key=f"cancel_button_{teacher_name}_{secure_id}", # Unique key
                    disabled=not is_enrolled,
                    use_container_width=True
                )

            # --- Button Actions (use translated success/error messages) ---
            if enroll_clicked:
                # Re-check conditions in case state changed between render and click
                current_enrollments_onclick = load_data(ENROLLMENTS_DB_PATH) # Load fresh
                current_teacher_list = current_enrollments_onclick.get(teacher_name, [])
                # Re-check capacity
                teacher_details_onclick = load_data(TEACHERS_DB_PATH).get(teacher_name, {})
                cap_onclick = teacher_details_onclick.get("enrollment_cap")
                unlimited_onclick = (cap_onclick is None or not isinstance(cap_onclick, int) or cap_onclick <= 0)
                is_full_onclick = False if unlimited_onclick else len(current_teacher_list) >= cap_onclick
                is_enrolled_onclick = user_name in current_teacher_list

                if not is_enrolled_onclick and not is_full_onclick:
                    current_teacher_list.append(user_name)
                    current_enrollments_onclick[teacher_name] = current_teacher_list
                    save_data(ENROLLMENTS_DB_PATH, current_enrollments_onclick)
                    # Use translated success message format string
                    success_format = lang.get("enroll_success", "Thank you, {name}! You are now enrolled in {teacher}'s class!")
                    st.success(success_format.format(name=user_name, teacher=teacher_name))
                    st.rerun()
                elif is_enrolled_onclick:
                     st.warning(lang.get("already_enrolled_warning", "Already enrolled."))
                elif is_full_onclick:
                     st.warning(lang.get("enrollment_full", "Enrollment Full")) # Should be caught by disabled state mostly

            if cancel_clicked:
                # Re-check condition
                current_enrollments_onclick = load_data(ENROLLMENTS_DB_PATH) # Load fresh
                if teacher_name in current_enrollments_onclick and user_name in current_enrollments_onclick[teacher_name]:
                    current_enrollments_onclick[teacher_name].remove(user_name)
                    if not current_enrollments_onclick[teacher_name]: # Remove teacher key if list empty
                        del current_enrollments_onclick[teacher_name]
                    save_data(ENROLLMENTS_DB_PATH, current_enrollments_onclick)
                    st.info(lang.get("enrollment_cancelled", "Enrollment has been cancelled.")) # Translated info
                    st.rerun()
                else:
                    # This case should be rare due to the disabled button state
                    st.error(lang.get("not_enrolled", "Your name was not found in the enrollment.")) # Translated error

            # --- Enrollment List Expander (use translated label) ---
            # Format the label string with count
            expander_label_format = lang.get("enrolled_label", "Enrolled Students") + " ({count})"
            with st.expander(expander_label_format.format(count=current_enrollment_count)):
                # Use the enrollment data loaded at the start of the loop for this display
                current_teacher_enrollments_display = enrollments.get(teacher_name, [])
                if current_teacher_enrollments_display:
                    for i, student_name in enumerate(current_teacher_enrollments_display, 1):
                        display_name = f"{i}. {student_name}" # Student names not translated
                        if student_name == user_name:
                            # Get translated "You" marker if translator available
                            you_marker = user_name # Fallback
                            if translator:
                                 you_marker = translate_text(translator, "You", lang_code)
                            display_name += f" **({you_marker})**"
                        st.markdown(display_name)
                else:
                    st.write(lang.get("no_enrollments", "No students enrolled yet.")) # Translated message
            st.markdown("---") # Separator between teachers
