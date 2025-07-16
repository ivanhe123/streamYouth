# Required library: pip install googletrans==4.0.0-rc1 streamlit pandas
import datetime
import streamlit as st
from streamlit_geolocation import streamlit_geolocation
from timezonefinder import TimezoneFinder
import pytz
import reverse_geocoder as rg  # For reverse geocoding
import pycountry             # For getting country name from code

import pycountry
import json
import shutil
import calendar
import os
import mimetypes
from zoneinfo import *
import hmac
import streamlit_autorefresh as st_autorefresh
from streamlit_date_picker import date_range_picker, date_picker, PickerType
import hashlib
import pandas as pd
import uuid
from itertools import chain
from datetime import timedelta
import time
from streamlit_geolocation import streamlit_geolocation
from streamlit_star_rating import st_star_rating

# --- Translation Setup (ONLY for dynamic content) ---
translator=None
AUTOPLAY_DELAY_SECONDS = 7
APPROX_MESSAGE_AREA_HEIGHT_PX = 90
BUTTON_HEIGHT_PX = 38  # Must match CSS
SPACER_HEIGHT_PX = max(0, (APPROX_MESSAGE_AREA_HEIGHT_PX - BUTTON_HEIGHT_PX) // 2)


def initialize_state(messages_data):
    """Initializes session state variables if they don't exist."""
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'autoplay_on' not in st.session_state:
        st.session_state.autoplay_on = True
    if 'last_interaction_time' not in st.session_state:
        st.session_state.last_interaction_time = time.time()
    if 'messages_data' not in st.session_state or st.session_state.messages_data != messages_data:
        st.session_state.messages_data = messages_data
        st.session_state.current_index = 0
        st.session_state.last_interaction_time = time.time()


def display_message_content_for_carousel():
    """Displays the current message content, styled to match the image."""
    if not st.session_state.messages_data:
        st.warning("No messages to display.")
        return

    idx = st.session_state.current_index
    message_data = st.session_state.messages_data[idx]

    # HTML structure for message content and bottom-right aligned user name
    # No outer border on this div, styling is internal
    message_html = f"""
    <div style="position: relative;
                min-height: {APPROX_MESSAGE_AREA_HEIGHT_PX}px; /* Helps with consistent layout */
                padding: 10px 5px; /* Top/bottom, Left/right padding */
                padding-bottom: 35px; /* Extra space for the user name at the bottom */
                font-family: 'Source Sans Pro', sans-serif, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                text-align: left;">
        <div style="font-size: 1em; /* Standard text size */
                    color: #262730; /* Dark text color, common in Streamlit */
                    margin-bottom: 20px; /* Space between message and name */
                    line-height: 1.6;">
            "{message_data['message']}"
        </div>
        <div style="position: absolute;
                    bottom: 5px; /* Position from bottom of parent */
                    right: 5px;  /* Position from right of parent */
                    font-size: 0.9em; /* Slightly smaller for attribution */
                    color: #4A4A4A; /* Dark grey for user name */
                    font-style: italic;">
            — {message_data['user']}
        </div>
    </div>
    """
    st.markdown(message_html, unsafe_allow_html=True)


def handle_autoplay(num_messages):
    """Handles the automatic swiping logic."""
    if not st.session_state.autoplay_on or num_messages <= 1:  # No autoplay if 1 or 0 messages
        return

    st_autorefresh(interval=AUTOPLAY_DELAY_SECONDS * 1000, limit=None, key="autoplay_refresher")

    current_time = time.time()
    time_since_last_interaction = current_time - st.session_state.last_interaction_time

    if time_since_last_interaction >= AUTOPLAY_DELAY_SECONDS:
        st.session_state.current_index = (st.session_state.current_index + 1) % num_messages
        st.session_state.last_interaction_time = current_time
        st.rerun()

def string_to_delta(string):
    splted=string.split(" days, ")
    if len(splted)==1:
        hours, minutes, seconds = map(int, splted[0].split(':'))
        return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)
    else:
        hours, minutes, seconds = map(int, splted[1].split(':'))
        return datetime.timedelta(days=int(splted[0]),hours=hours,minutes=minutes,seconds=seconds)

def string_to_params(string):

    splted = string.split(" days, ")
    if len(splted) == 1:
        hours, minutes, seconds = map(int, splted[0].split(':'))
        return 0, hours, minutes, seconds
    else:
        hours, minutes, seconds = map(int, splted[1].split(':'))
        return int(splted[0]), hours, minutes, seconds

def get_timezone_from_location_name(country_name_or_code, city_name, state_province_name=None):
    """
    Attempts to find the IANA timezone string for a given location (country, city, optionally state/province)
    using the offline geonamescache library.

    Args:
        country_name_or_code (str): The full country name (e.g., "United States") or its ISO 3166-1 alpha-2 code (e.g., "US").
        city_name (str): The name of the city.
        state_province_name (str, optional): The name of the state or province.
                                             This helps disambiguate cities with the same name. Defaults to None.

    Returns:
        str or None: The IANA timezone string (e.g., "America/New_York") if found, otherwise None.
    """
    gc = geonamescache.GeonamesCache()

    # 1. Normalize country input to country code
    country_code = None
    countries_data = gc.get_countries() # Dict of country_code: {details}
    country_name_or_code_lower = country_name_or_code.lower()

    if len(country_name_or_code_lower) == 2: # Assume it's a code
        if country_name_or_code_lower.upper() in countries_data:
            country_code = country_name_or_code_lower.upper()
    else: # Assume it's a name
        for code, details in countries_data.items():
            if details.get('name', '').lower() == country_name_or_code_lower:
                country_code = code
                break
            # Check common aliases or alternative names if needed (more complex)

    if not country_code:
        # print(f"Debug: Country '{country_name_or_code}' not found in geonamescache.")
        return None

    # 2. Get cities and filter by country and name
    cities_data = gc.get_cities() # Dict of city_id: {details}
    candidate_cities = []
    city_name_lower = city_name.lower()
    state_province_name_lower = state_province_name.lower() if state_province_name else None

    for city_id, city_details in cities_data.items():
        if city_details.get('countrycode') == country_code and \
           city_details.get('name', '').lower() == city_name_lower:

            # If state/province is provided, try to match it
            if state_province_name_lower:
                # 'admin1' in geonamescache city data often holds the state/province name or code.
                # It might not always be the full name, could be an abbreviation or code.
                city_admin1 = city_details.get('admin1', '').lower()
                if state_province_name_lower in city_admin1 or city_admin1 in state_province_name_lower : # Partial match
                    candidate_cities.append(city_details)
                # For more precise matching, you might need admin1 code lookup if available
            else:
                candidate_cities.append(city_details)

    if not candidate_cities:
        # print(f"Debug: City '{city_name}' in country '{country_code}' not found.")
        return None

    # 3. Handle multiple matches or get timezone
    # If multiple cities match (e.g., "Springfield" in "US"), prioritize by population or return first valid.
    # For simplicity, we'll take the first one with a valid timezone.
    # A more robust solution might sort by population if available (city_details.get('population'))
    # or require state/province if multiple are found without it.

    found_timezone = None
    for city_info in sorted(candidate_cities, key=lambda c: c.get('population', 0), reverse=True): # Prioritize by population
        tz_name = city_info.get('timezone')
        if tz_name:
            # Validate if it's a known timezone by pytz to be safe
            try:
                pytz.timezone(tz_name)
                found_timezone = tz_name
                break # Found a valid timezone for a matching city
            except pytz.exceptions.UnknownTimeZoneError:
                # print(f"Debug: Geonamescache listed timezone '{tz_name}' for {city_name} but pytz doesn't know it.")
                continue # Try next candidate city if any

    if found_timezone:
        return found_timezone
    else:
        # print(f"Debug: No valid timezone found for the specified location criteria among candidates.")
        return None
# --- End Translation Setup ---

# --- Configuration ---
st.set_page_config(layout="wide")  # Use wide layout for admin editors
st.markdown("""<style>.st-emotion-cache-1p1m4ay{ visibility:hidden }</style>""", unsafe_allow_html=True)
USER_DB_PATH = "user_db.json"
ENROLLMENTS_DB_PATH = "enrollments.json"
TEACHERS_DB_PATH = "teachers.json"
SWITCH_DB_PATH = "switch.json"

# --- RESTORED Bilingual Texts Dictionary (for UI elements) ---
texts = {
    "English": {
        "ERR_NO_RATE": "Please give the teacher a Feedback!", "autcompl":"Autocomplete Location and Timezone info (might take a few seconds)","mancompl":"Enter Manually",
        "RATED": "Finished Feedback this teacher at {time}! Thank You!",
        "explanation": "Explain why did you give {name} this rating",
        "page_title": "PLE Youth Enrollment", "language_label": "Choose Language",
        "teacher_search_label": "Search for a teacher by name:", "page_title_rate": "PLE Youth Rating",
        "teacher_not_found_error": "No active teacher found with that search term.",
        "enter_teacher_info": "Displaying all available teachers. Use the search box above to filter.",
        "teaches": "Teaches", "to_grade": "grade", "enroll_button": "Enroll", "cancel_button": "Cancel Enrollment",
        "enroll_success": "Thank you, {name}! You are now enrolled in {teacher}'s class!",
        "enrollment_cancelled": "Enrollment has been cancelled.",
        "register_prompt": "Welcome! Please register by entering the student's details below:", "teach_reg_p":"Welcome! Please register by entering some information about yourself",
        "register_button": "Register",
        "logged_in": "Logged in as: {name}", "enrolled_label": "Enrolled Students",
        "no_enrollments": "No students enrolled yet.", "no_rates": "You Didn't have any teacher to rate.",
        "not_enrolled": "Your name was not found in the enrollment.",
        "name_required": "Please enter your name to register.",
        "no_teachers_available": "No teachers are currently available for enrollment.",
        "enrollment_full": "Enrollment Full", "no_teachers_rating_available": "No teacher available for you to rate.",
        "user_enrollment_caption": "Enrolled: {count} / {cap}", "unlimited": "Unlimited",
        "grade_select_label": "Select Grade",
        "all_grades": "All", "refresh": "Refresh", "register_name_label": "Student's English Full Name", "reg_name_t":"Your English Full Name",
        "register_grade_label": "Current Grade", "reg_g_t":"The Grade You Teach (You can change it afterwards)", "reg_c_t":"The Course You Teach (You can change it afterwards)", "reg_desc":"A little Description about yourself or your Teaching Experience (You can change it afterwards)",
        "register_raz_label": "RAZ Level",  # <-- Added RAZ Label
        "register_country_label": "Country", "register_state_label": "State/Province", "register_city_label": "City",
        "select_country": "--- Select Country ---", "select_state": "--- Select State/Province ---",
        "select_city": "--- Select City ---",
        "fill_all_fields": "Please fill in Name and select a valid Country, State/Province, City, and Time Zone.",
        # RAZ not mandatory here, adjust if needed
        "already_enrolled_warning": "Already enrolled.", "registered_success": "Registered {name}! Reloading page.",
        "you_marker": "You",
        "save_settings_button": "Save Settings", "settings_updated_success": "Settings updated successfully!",
        "class_info_header": "Class Information",
        "subject_en_label": "Subject (English)", "grade_label": "Grade", "enrollment_limit_header": "Enrollment Limit",
        "max_students_label": "Maximum Students (0=unlimited)", "class_status_header": "Class Status",
        "class_rating": "Class Rating", "class_no_rating": "No Ratings Yet",
        "enrollment_status_header": "Enrollment Status", "rate_class": "Rate Your Experience with {name}",
        "status_active": "Active (Students can see)", "status_cancelled": "Cancelled (Students cannot see)",
        "enrollment_active": "Open (Students can enroll)", "enrollment_blocked": "Closed (Students cannot enroll)",
        "cancel_class_button": "Cancel Class (Hide)", "reactivate_class_button": "Reactivate Class (Show)",
        "block_enroll_button": "Close Enrollment", "reactivate_enroll_button": "Open Enrollment",
        "enrollment_overview_header": "Enrollment Overview", "current_enrollment_metric": "Current Enrollment",
        "enrolled_students_list_header": "Enrolled Students:",
        "teacher_dashboard_title": "Teacher Dashboard: {name}", "teacher_logout_button": "Logout",
        "teacher_login_title": "Teacher Portal Login",
        "teacher_id_prompt": "Enter your Teacher ID:", "login_button": "Login",
        "invalid_teacher_id_error": "Invalid Teacher ID.",
        "admin_dashboard_title": "Admin Dashboard", "admin_password_prompt": "Enter Admin Password:",
        "admin_access_granted": "Access granted.",
        "refresh_data_button": "Refresh Data from Files", "manage_teachers_header": "Manage Teachers",
        "enrollment_closed": "Enrollment Has Been Closed for this Class",
        "manage_teachers_info": "Add/edit details. Set cap=0 for unlimited. Use trash icon to remove.",
        "save_teachers_button": "Save Changes to Teachers",
        "manage_students_header": "Manage Registered Students", "save_students_button": "Save Changes to Students",
        "save_s-t_button": "Save Changes",
        "manage_assignments_header": "Teacher-Student Assignments",
        "save_assignments_button": "Save Changes to Assignments",
        "assignment_student_details_header": "Student Details (Read-Only)",  # For assignments editor
        "raz_level_column": "RAZ Level",  # For admin editors
        "location_column": "Location",  # For admin assignments editor
        "teacher_description_label_en": "Description (English)",
        "teacher_description_label_zh": "Description (Chinese)",
        "teacher_description_header": "Teacher Description",
        "no_description_available": "No description available.",  # For Student View
        "admin_manage_teachers_desc_en": "Description EN",  # Column header in Admin
        "admin_manage_teachers_desc_zh": "Description ZH", "selectzone": "Select your time zone"
    },
    "中文": {
        "ERR_NO_RATE": "请给老师一个评分！", "RATED": "已在{time}完成对老师的反馈！感谢！","autcompl":"自动输入位置并时区信息（处理需要几秒钟）","mancompl":"手动输入",
        "explanation": "请解释你为什么会给{name}老师打这个分数？",
        "page_title": "PLE Youth 教师搜索与注册", "language_label": "选择语言",
        "teacher_search_label": "请输入教师姓名搜索：", "page_title_rate": "PLE Youth 教师搜索与评分",
        "teacher_not_found_error": "没有匹配的可用教师。",
        "enter_teacher_info": "正在显示所有可用教师。使用上方搜索框筛选。",
        "teaches": "授课", "to_grade": "年级", "enroll_button": "报名", "cancel_button": "取消报名",
        "enroll_success": "谢谢, {name}! 你已注册到 {teacher} 的课程！", "enrollment_cancelled": "报名已取消。",
        "register_prompt": "欢迎！请通过输入学生的详细信息完成注册：", "register_button": "注册", "teach_reg_p":"欢迎！请输入你的一些信息完成注册：",
        "logged_in": "已登录: {name}", "enrolled_label": "已报名的学生", "no_enrollments": "当前没有报名的学生。",
        "no_rates": "当前没有可反馈的老师",
        "not_enrolled": "未找到你的报名记录。", "name_required": "请输入你的名字以注册。",
        "no_teachers_available": "目前没有可报名的教师。", "enrollment_full": "报名已满",
        "enrollment_closed": "此课程报名以关闭", "no_teachers_rating_available": "你当前没有可评分的老师",
        "user_enrollment_caption": "已报名: {count} / {cap}", "unlimited": "无限制", "grade_select_label": "选择年级",
        "all_grades": "所有年级", "refresh": "刷新", "register_name_label": "学生英文全名", "reg_name_t":"请输入你的英文全名",
        "register_grade_label": "当前年级", "reg_g_t":"你教的年级（以后可以改）","reg_c_t":"你教的学科（以后可以改）", "reg_desc":"简单介绍一下你自己或你的教学经历（以后可以改）",
        "register_raz_label": "RAZ 等级",  # <-- Added RAZ Label
        "register_country_label": "国家", "register_state_label": "州/省", "register_city_label": "城市",
        "select_country": "--- 选择国家 ---", "select_state": "--- 选择州/省 ---", "select_city": "--- 选择城市 ---",
        "fill_all_fields": "请填写姓名并选择有效的国家、州/省、城市和时区。",  # RAZ not mandatory here, adjust if needed
        "already_enrolled_warning": "已报名。", "registered_success": "已注册 {name}! 正在重新加载页面。",
        "you_marker": "你",
        "save_settings_button": "保存设置", "settings_updated_success": "设置已成功更新！",
        "class_info_header": "课程信息",
        "subject_en_label": "科目（英文）", "grade_label": "年级", "enrollment_limit_header": "报名人数限制",
        "max_students_label": "最多学生数（0表示无限制）", "class_status_header": "课程状态", "class_rating": "课程评分",
        "class_no_rating": "还没有评分", "enrollment_status_header": "报名状态",
        "rate_class": "给你和{name}老师的学习经历打分",
        "status_active": "开放（学生可以看到）", "status_cancelled": "已取消（学生无法看到）",
        "enrollment_active": "开放（学生可以报名）", "enrollment_blocked": "关闭（学生不可以报名）",
        "cancel_class_button": "取消课程（隐藏）", "reactivate_class_button": "重新激活课程（显示）",
        "block_enroll_button": "关闭报名", "reactivate_enroll_button": "开放报名",
        "enrollment_overview_header": "报名概览", "current_enrollment_metric": "当前报名人数",
        "enrolled_students_list_header": "已报名学生：",
        "teacher_dashboard_title": "教师仪表板：{name}", "teacher_logout_button": "登出",
        "teacher_login_title": "教师门户登录",
        "teacher_id_prompt": "输入您的教师ID：", "login_button": "登录", "invalid_teacher_id_error": "无效的教师ID。",
        "admin_dashboard_title": "管理员仪表板", "admin_password_prompt": "输入管理员密码：",
        "admin_access_granted": "授权成功。",
        "refresh_data_button": "从文件刷新数据", "manage_teachers_header": "管理教师",
        "manage_teachers_info": "添加/编辑详情。设置人数上限为0表示无限制。使用垃圾桶图标删除。",
        "save_teachers_button": "保存对教师的更改",
        "manage_students_header": "管理已注册学生", "save_students_button": "保存对学生的更改",
        "save_s-t_button": "保存更改",
        "manage_assignments_header": "师生分配", "save_assignments_button": "保存分配更改",
        "assignment_student_details_header": "学生详情（只读）",  # For assignments editor
        "raz_level_column": "RAZ 等级",  # For admin editors
        "location_column": "位置",  # For admin assignments editor
        "teacher_description_label_en": "描述（英文）",
        "teacher_description_label_zh": "描述（中文）",
        "teacher_description_header": "教师描述",  # 教师仪表板部分
        "no_description_available": "暂无描述。",  # 学生视图
        "admin_manage_teachers_desc_en": "描述 EN",  # 管理员中的列标题
        "admin_manage_teachers_desc_zh": "描述 ZH", "selectzone": "请选择你的时区"
    }
}
# --- Simplified Location Data (English Only) ---
location_data = {
    "USA": {"California": ["Los Angeles", "San Francisco"], "New York": ["New York City", "Buffalo"]},
    "China": {"Beijing Municipality": ["Beijing"], "Shanghai Municipality": ["Shanghai"]},
    "Canada": {"Ontario": ["Toronto", "Ottawa"], "Quebec": ["Montreal", "Quebec City"]},
    # Add more...
}

timezozs = {
    "China": "Asia/Shanghai"
}
# Define the order of days for consistent numerical representation
DAYS_OF_WEEK = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
MINUTES_IN_DAY = 24 * 60
MINUTES_IN_WEEK = 7 * MINUTES_IN_DAY


def time_str_to_minutes(time_str):
    t = datetime.datetime.strptime(time_str, "%H:%M").time()
    return t.hour * 60 + t.minute


def get_date_for_day_of_week(current_date_str, target_day_name):
    current_date = datetime.strptime(current_date_str, "%Y/%m/%d").date()

    target_day_name_lower = target_day_name.lower()
    if target_day_name_lower not in DAYS_OF_WEEK:
        print(f"Error: Invalid target_day_name: {target_day_name}. Expected one of {list(DAYS_OF_WEEK.keys())}.")
        return None

    # Get the weekday number for the current date (Monday is 0 and Sunday is 6)
    current_day_of_week_num = current_date.weekday()

    # Get the weekday number for the target day
    target_day_of_week_num = DAYS_OF_WEEK[target_day_name_lower]

    # Calculate the difference in days
    # This will find the target day within the current week (Mon-Sun)
    # If current_day is Thursday (3) and target is Tuesday (1), diff is 1 - 3 = -2 days
    # If current_day is Tuesday (1) and target is Thursday (3), diff is 3 - 1 = +2 days
    day_difference = target_day_of_week_num - current_day_of_week_num

    # Calculate the target date by adding the difference to the current date
    target_date = current_date + timedelta(days=day_difference)

    return target_date.strftime("%Y-%m-%d")


def day_time_to_total_minutes(day_str, time_str):
    day_str_lower = day_str.lower()
    day_offset_minutes = DAYS_OF_WEEK[day_str_lower] * MINUTES_IN_DAY
    time_offset_minutes = time_str_to_minutes(time_str)
    return day_offset_minutes + time_offset_minutes


def is_within_range(start_day_str, start_time_str, end_day_str, end_time_str, current_day_str, current_time_str):
    start_total_minutes = day_time_to_total_minutes(start_day_str, start_time_str)
    end_total_minutes = day_time_to_total_minutes(end_day_str, end_time_str)
    current_total_minutes = day_time_to_total_minutes(current_day_str, current_time_str)

    if end_total_minutes < start_total_minutes:

        return current_total_minutes >= start_total_minutes or \
            current_total_minutes <= end_total_minutes
    else:

        return start_total_minutes <= current_total_minutes <= end_total_minutes


# --- File Database Helper Functions ---
def load_data(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read(); return json.loads(content) if content else {}
        except (json.JSONDecodeError, IOError) as e:
            st.error(f"Error loading {path}: {e}"); return {}
    return {}


def save_data(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        st.error(f"Error saving {path}: {e}")


# --- Load file databases ---
user_database_global = load_data(USER_DB_PATH)
enrollments_global = load_data(ENROLLMENTS_DB_PATH)
teachers_database_global = load_data(TEACHERS_DB_PATH)
broadcasted_info = load_data(SWITCH_DB_PATH)
if (broadcasted_info == {}):
    save_data(SWITCH_DB_PATH, {"rating": False, "all_hidden": False, "all_closed": False})
    broadcasted_info = load_data(SWITCH_DB_PATH)
days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
allowed_zms=["Asia/Shanghai","America/Los_Angeles","America/Chicago",'America/New_York','Europe/Berlin',"Japan","America/Sao_Paulo",'America/Mexico_City',"Asia/Dhaka",]
avtimezones=[x for x in list(available_timezones()) if x in allowed_zms]
# --- Encryption & ID Generation ---
#if "secret_key" not in st.secrets: st.error("`secret_key` missing."); st.stop()
SECRET_KEY = st.secrets["secret_key"]


def encrypt_id(plain_id: str) -> str: return hmac.new(SECRET_KEY.encode(), plain_id.encode(),
                                                      hashlib.sha256).hexdigest()


def generate_teacher_id(): return uuid.uuid4().hex


# --- Validate Teacher ID ---
def validate_teacher_id(entered_id: str):
    current_teachers_db = load_data(TEACHERS_DB_PATH)  # Load fresh
    for name, details in current_teachers_db.items():
        if details.get("id") == entered_id: return name, details
    return None, None


def find_date_of_day_in_current_week(target_day_name: str, reference_date: datetime.date = None) -> datetime.date:
    if reference_date is None:
        reference_date = datetime.date.today()

    days_of_week = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    target_day_name_lower = target_day_name.lower()
    if target_day_name_lower not in days_of_week:
        raise ValueError(
            f"Invalid day name: '{target_day_name}'. "
            f"Please use one of {list(days_of_week.keys())}."
        )

    target_weekday_int = days_of_week[target_day_name_lower]
    reference_weekday_int = reference_date.weekday()  # Monday is 0 and Sunday is 6

    days_difference = target_weekday_int - reference_weekday_int

    target_date = reference_date + datetime.timedelta(days=days_difference)
    return target_date


def is_date_in_range(start_date: datetime.date, end_date: datetime.date, date_to_check: datetime.date = None) -> bool:
    if date_to_check is None:
        date_to_check = datetime.date.today()

    # Ensure the range is valid (start_date should not be after end_date)
    if start_date > end_date:
        # print(f"Warning: start_date ({start_date}) is after end_date ({end_date}). Invalid range.")
        return False

    return start_date <= date_to_check <= end_date
BASE_UPLOAD_DIRECTORY = "user_specific_uploads" # Main folder for all user uploads
SUPPORTED_TYPES = ["pptx", "xlsx", "xls", "docx", "txt", "pdf"]
def save_file_for_user(user_id, uploaded_file_obj):
    """
    Saves the uploaded file to a user-specific directory.
    Deletes any previously existing files in that user's directory.
    Returns the path to the saved file and the file bytes.
    """
    if not user_id:
        raise ValueError("User ID cannot be empty.")

    # Sanitize user_id for directory naming (basic example)
    # In a real app, use a more robust sanitization or hashing method
    safe_user_id_folder_name = "".join(c for c in user_id if c.isalnum() or c in ('_', '-')).rstrip()
    if not safe_user_id_folder_name:
        raise ValueError("User ID resulted in an invalid folder name after sanitization.")

    user_specific_dir = os.path.join(BASE_UPLOAD_DIRECTORY, safe_user_id_folder_name)

    # 1. Create the base upload directory if it doesn't exist
    os.makedirs(BASE_UPLOAD_DIRECTORY, exist_ok=True)

    # 2. Clear and create/recreate the user's specific directory
    if os.path.exists(user_specific_dir):
        # Delete all contents of the user's directory
        for item_name in os.listdir(user_specific_dir):
            item_path = os.path.join(user_specific_dir, item_name)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path) # Use shutil to remove directories
            except Exception as e:
                st.warning(f"Could not delete old item {item_path}: {e}")
    os.makedirs(user_specific_dir, exist_ok=True) # Ensure it exists after clearing

    # 3. Save the new file
    file_bytes = uploaded_file_obj.getvalue()
    original_filename = uploaded_file_obj.name
    save_path = os.path.join(user_specific_dir, original_filename)

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    return save_path, file_bytes, original_filename, uploaded_file_obj.type

# --- Teacher Dashboard (Displaying Names from IDs) ---
def teacher_dashboard():
    global teachers_database_global, enrollments_global

    admin_lang = texts["English"]  # Teacher dashboard uses English UI elements for now

    # ... (Title, Logout, Refresh, Teacher Details Loading - unchanged) ...
    st.title(f"{admin_lang['teacher_dashboard_title'].format(name=st.session_state.teacher_name)}")
    if st.button(admin_lang["teacher_logout_button"], key="teacher_logout"):
        keys_to_delete = ["teacher_logged_in", "teacher_id", "teacher_name"]
        for key in keys_to_delete:
            if key in st.session_state: del st.session_state[key]
        st.success("Logged out.");
        st.rerun()
    if st.button(admin_lang["refresh"]): st.rerun()
    st.markdown("---")
    teacher_name = st.session_state.teacher_name
    teacher_id = st.session_state.teacher_id
    current_teachers_db = load_data(TEACHERS_DB_PATH)
    teacher_details = current_teachers_db.get(teacher_id)
    if not teacher_details: st.error("Teacher data not found."); st.stop()
    ratt = teacher_details.get("rating", None)
    if teacher_details.get("rated", None) != None:
        if teacher_details.get("rated", None) == []:
            teacherratt = None

        else:

            teachrat = list(chain(*list(teacher_details.get("rated", None).values())))
            print(teachrat)
            smup = [m["stars"] for m in teachrat]

            teacherratt = sum(smup)
        teacher_details["rating"] = str(teacherratt)
    else:
        teacherratt = None
        teacher_details["rating"] = str(teacherratt)

    current_teachers_db[teacher_id] = teacher_details
    save_data(TEACHERS_DB_PATH, current_teachers_db)
    teacher_details = load_data(TEACHERS_DB_PATH)[teacher_id]
    print(current_teachers_db[teacher_id])
    ratt = teacher_details.get("rating", None)
    print(ratt)

    if (ratt != None and ratt.isdigit() and int(ratt) >= 0):
        st_star_rating(label=admin_lang["class_rating"], maxValue=5,
                       defaultValue=int(teacher_details.get("rating", "0")), key="rating", read_only=True)
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
        current_teachers_db[teacher_id]["is_active"] = new_status
        save_data(TEACHERS_DB_PATH, current_teachers_db);
        teachers_database_global = current_teachers_db
        st.success("Class status updated.");
        st.rerun()

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
        current_teachers_db[teacher_id]["allow_enroll"] = new_status1
        print(current_teachers_db[teacher_id]["allow_enroll"])
        save_data(TEACHERS_DB_PATH, current_teachers_db);
        teachers_database_global = current_teachers_db
        st.success("Enrollment status updated.");
        st.rerun()

    # ... (Class Settings Form - unchanged) ...
    st.markdown("---")
    st.subheader(admin_lang["class_info_header"])
    with st.form("edit_teacher_form"):
        # ... (Subject, Grade, Cap, Descriptions inputs - unchanged) ...
        st.write("**Class Details & Limit**");
        col1, col2 = st.columns(2)
        with col1: new_subject_en = st.text_input(admin_lang["subject_en_label"],
                                                  value=teacher_details.get("subject_en", ""))
        with col2: new_grade = st.text_input(admin_lang["grade_label"], value=teacher_details.get("grade", ""))
        current_cap = teacher_details.get("enrollment_cap");
        cap_value = current_cap if current_cap is not None else 0
        new_cap = st.number_input(admin_lang["max_students_label"], min_value=0, value=cap_value, step=1, format="%d",
                                  key="teacher_edit_cap")
        st.markdown("---");
        st.write(f"**{admin_lang['teacher_description_header']}**")
        new_desc_en = st.text_area(admin_lang["teacher_description_label_en"],
                                   value=teacher_details.get("description_en", ""), height=150)
        new_desc_zh = st.text_area(admin_lang["teacher_description_label_zh"],
                                   value=teacher_details.get("description_zh", ""), height=150)
        print(teacher_id)
        # File uploader widget
        uploaded_file = st.file_uploader(
            "Upload your Courseware",
            type=SUPPORTED_TYPES,
            accept_multiple_files=False  # Process one file at a time
        )

        if uploaded_file is not None:
            save_file_for_user(teacher_id,uploaded_file)
        # ... (Save button logic - unchanged) ...
        submitted = st.form_submit_button(admin_lang["save_settings_button"])
        if submitted:
            processed_cap = int(new_cap) if new_cap > 0 else None
            current_teachers_db[teacher_id].update(
                {"subject_en": new_subject_en.strip(), "grade": new_grade.strip(), "enrollment_cap": processed_cap,
                 "description_en": new_desc_en.strip(), "description_zh": new_desc_zh.strip()})
            save_data(TEACHERS_DB_PATH, current_teachers_db);
            teachers_database_global = current_teachers_db
            st.success(admin_lang["settings_updated_success"]);
            st.rerun()

    st.markdown("---")
    st.subheader(admin_lang["enrollment_overview_header"])
    # --- Enrollment Overview (Displaying names looked up by ID) ---
    current_enrollments = load_data(ENROLLMENTS_DB_PATH)  # Load fresh enrollments (student IDs)
    user_db_for_display = load_data(USER_DB_PATH)  # Load fresh user data for name lookup

    enrolled_student_ids = current_enrollments.get(teacher_id, [])
    enrollment_count = len(enrolled_student_ids)
    display_cap = teacher_details.get("enrollment_cap")  # None or int
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
            elif isinstance(student_info, str):  # Handle old format if necessary
                enrolled_student_names.append(f"{student_info} (ID: {s_id})")
            else:
                enrolled_student_names.append(f"Unknown ID: {s_id}")

        # Display sorted names
        for i, student_name_display in enumerate(sorted(enrolled_student_names), 1):
            st.markdown(f"{i}. {student_name_display}")
    else:
        st.info(admin_lang["no_enrollments"])


def find_key_by_value(nested_dict, target_value):
    for key, sub_dict in nested_dict.items():
        if isinstance(sub_dict, dict) and target_value in sub_dict.values():
            return key
    return None


# --- Admin Route (Updated for Teacher Description) ---
def admin_route():
    global user_database_global, enrollments_global, teachers_database_global
    admin_lang = texts["English"]  # Admin panel uses English UI text

    st.title(admin_lang["admin_dashboard_title"])
    # ... (Password check, Refresh Button - unchanged) ...
    
    if "passcode" not in st.secrets: st.error("Admin `passcode` missing."); st.stop()
    timezone_str=None
    admin_password = st.text_input(admin_lang["admin_password_prompt"], type="password", key="admin_pw")

    st.write("👇Login (might take a few seconds)")
    location_data = streamlit_geolocation()  # Use a unique key

    if location_data and 'latitude' in location_data and 'longitude' in location_data:
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')

        if latitude is not None and longitude is not None:

            # Initialize TimezoneFinder
            # This object can be computationally expensive to create,
            # so for performance in a real app, you might consider caching it
            # or creating it once at the start of the script if not using Streamlit's rerun magic.
            # However, for this simple case, direct initialization is fine.
            tf = TimezoneFinder()

            # Get the timezone string
            # Note: timezone_at() expects longitude first, then latitude
            timezone_str = tf.timezone_at(lng=longitude, lat=latitude)

            if timezone_str:
                st.success(f"Estimated Timezone: {timezone_str}")
                if "timezone_admin" not in st.session_state:
                    st.session_state.timezone_admin = pytz.timezone(timezone_str)
    if not timezone_str: st.stop()
    if admin_password != st.secrets["passcode"]: st.error("Incorrect password."); st.stop()
    st.success(admin_lang["admin_access_granted"])
    if st.button(admin_lang["refresh_data_button"]):
        user_database_global = load_data(USER_DB_PATH);
        enrollments_global = load_data(ENROLLMENTS_DB_PATH);
        teachers_database_global = load_data(TEACHERS_DB_PATH)
        st.rerun()
    st.markdown("---")

    # --- Manage Teachers (Unchanged) ---
    st.subheader(admin_lang["manage_teachers_header"])
    st.markdown(admin_lang["manage_teachers_info"])
    # ... (Teacher editor and save logic - unchanged from previous version) ...
    # Data loading and preparation
    teachers_list = [];
    temp_teachers_db_for_edit = load_data(TEACHERS_DB_PATH);
    needs_saving_defaults = False
    for name, details in temp_teachers_db_for_edit.items():
        print(temp_teachers_db_for_edit)
        # if "id" not in details: details["id"] = generate_teacher_id(); needs_saving_defaults = True
        if "is_active" not in details: details["is_active"] = True; needs_saving_defaults = True
        if "enrollment_cap" not in details: details["enrollment_cap"] = None; needs_saving_defaults = True
        if "description_en" not in details: details["description_en"] = ""; needs_saving_defaults = True
        if "description_zh" not in details: details["description_zh"] = ""; needs_saving_defaults = True
        if "rating" not in details: details["rating"] = None; needs_saving_defaults = True
        if "allow_enroll" not in details: details["allow_enroll"] = True; needs_saving_defaults = True
        if "rated" not in details: details["rated"] = []; needs_saving_defaults = True
        if "timezone" not in details: details["timezone"]="";
        print(details)
        teachers_list.append(
            {"Teacher ID": name, "Teacher Name": details["name"], "Subject (English)": details.get("subject_en", ""),
             "Description (English)": details.get("description_en", ""),
             "Description (Chinese)": details.get("description_zh", ""), "Grade": details.get("grade", ""),
             "Timezone":details.get("timezone",""),
             "Is Active": details.get("is_active"), "Rating": details.get("rating"),
             "Allow Enroll": details.get("allow_enroll"),
             "Enrollment Cap": details.get("enrollment_cap") if details.get("enrollment_cap") is not None else 0})

    if needs_saving_defaults:
        save_data(TEACHERS_DB_PATH, temp_teachers_db_for_edit);
        teachers_database_global = temp_teachers_db_for_edit;
        st.info("Applied defaults to teachers. Data saved.")
    columns_teacher = ["Teacher ID", "Teacher Name", "Enrollment Cap", "Subject (English)", "Grade",
                       "Description (English)", "Description (Chinese)", "Rating",
                       "Timezone",
                       "Allow Enroll", "Is Active"];
    teachers_df = pd.DataFrame(teachers_list, columns=columns_teacher) if teachers_list else pd.DataFrame(
        columns=columns_teacher)
    # Teacher editor UI
    edited_teachers_df = st.data_editor(teachers_df, num_rows="dynamic", key="teacher_editor", use_container_width=True,
                                        hide_index=True,
                                        column_config={"Teacher ID": st.column_config.TextColumn("ID", disabled=True),
                                                       "Teacher Name": st.column_config.TextColumn("Name",
                                                                                                   required=True),
                                                       "Subject (English)": st.column_config.TextColumn("Subject EN"),
                                                       "Description (English)": st.column_config.TextColumn(
                                                           admin_lang["admin_manage_teachers_desc_en"]),
                                                       "Description (Chinese)": st.column_config.TextColumn(
                                                           admin_lang["admin_manage_teachers_desc_zh"]),
                                                       "Grade": st.column_config.TextColumn("Grade"),
                                                       "Rating": st.column_config.TextColumn("Class Rating"),
                                                       "Timezone": st.column_config.TextColumn("Timezone"),
                                                       "Allow Enroll": st.column_config.CheckboxColumn("Allow Enroll?"),
                                                       "Is Active": st.column_config.CheckboxColumn("Active?"),
                                                       "Enrollment Cap": st.column_config.NumberColumn(
                                                           "Cap (0=unlimited)", min_value=0, step=1, format="%d")},
                                        column_order=columns_teacher)
    # Teacher save logic
    if st.button(admin_lang["save_teachers_button"]):
        # ... (Teacher saving logic identical to previous version) ...
        original_teachers_data = temp_teachers_db_for_edit;
        new_teachers_database = {};
        error_occurred = False;
        seen_names = set();
        processed_ids = set()
        for index, row in edited_teachers_df.iterrows():
            name = row["Teacher Name"];
            teacher_id = row["Teacher ID"];
            enrollment_cap_input = row["Enrollment Cap"]
            is_new_teacher = pd.isna(teacher_id) or str(teacher_id).strip() == "";
            if is_new_teacher: teacher_id = generate_teacher_id()
            if pd.isna(name) or str(name).strip() == "": st.error(
                f"Row {index + 1}: Name empty."); error_occurred = True; continue
            name = str(name).strip()
            if name in seen_names: st.error(
                f"Row {index + 1}: Duplicate Name '{name}'."); error_occurred = True; continue
            for existing_name, existing_details in original_teachers_data.items():
                if existing_details.get("id") != teacher_id and existing_name == name: st.error(
                    f"Row {index + 1}: Name '{name}' conflict."); error_occurred = True; break
            if error_occurred: continue
            seen_names.add(name);
            processed_ids.add(teacher_id)
            processed_cap = None;
            if pd.notna(enrollment_cap_input):
                try:
                    cap_int = int(enrollment_cap_input); processed_cap = cap_int if cap_int > 0 else None
                except (ValueError, TypeError):
                    st.error(f"Row {index + 1}: Invalid Cap."); error_occurred = True; continue
            original_details = next((d for _, d in original_teachers_data.items() if d.get("id") == teacher_id), None);
            current_is_active = original_details.get("is_active", True) if original_details else True

            desc_en = str(row["Description (English)"]).strip() if pd.notna(row["Description (English)"]) else "";
            desc_zh = str(row["Description (Chinese)"]).strip() if pd.notna(row["Description (Chinese)"]) else ""
            rat = row["Rating"]
            if (row["Allow Enroll"] == None):
                allow_enroll = True
            else:
                allow_enroll = row["Allow Enroll"]
            rtd = original_teachers_data.get("name", False)
            if rtd:
                rtd = original_teachers_data["name"]["rated"]
            else:
                rtd = ({})
            new_teachers_database[teacher_id] = {"name": name, "subject_en": str(row["Subject (English)"]) if pd.notna(
                row["Subject (English)"]) else "", "grade": str(row["Grade"]) if pd.notna(row["Grade"]) else "",
                                                 "description_en": desc_en, "description_zh": desc_zh,
                                                 "is_active": current_is_active, "allow_enroll": allow_enroll,
                                                 "enrollment_cap": processed_cap, "rated": rtd}
        deleted_teacher_names = [n for n, d in original_teachers_data.items() if d.get("id") not in processed_ids]
        if not error_occurred:

            save_data(TEACHERS_DB_PATH, new_teachers_database);
            teachers_database_global = new_teachers_database;
            st.success("Teacher data updated!")
            if deleted_teacher_names:
                enrollments_updated = False;
                current_enrollments = load_data(ENROLLMENTS_DB_PATH);
                new_enrollments_after_delete = current_enrollments.copy()
                for removed_name in deleted_teacher_names:
                    if removed_name in new_enrollments_after_delete:
                        del new_enrollments_after_delete[removed_name]
                        enrollments_updated = True
                        st.warning(f"Removed enrollments: {removed_name}")
                if enrollments_updated:
                    save_data(ENROLLMENTS_DB_PATH,new_enrollments_after_delete)
                    enrollments_global = new_enrollments_after_delete
            st.rerun()

        else:
            st.warning("Fix errors before saving teacher changes.")

    st.markdown("---")

    # --- Manage Registered Students (Update enrollment removal logic) ---
    st.subheader(admin_lang["manage_students_header"])
    # ... (Student list preparation and editor display - unchanged) ...
    students_list = [];
    temp_user_db_for_edit = load_data(USER_DB_PATH)
    for user_id, user_info in temp_user_db_for_edit.items():
        if isinstance(user_info, dict):
            students_list.append(
                {"Encrypted ID": user_id, "Name": user_info.get("name", ""), "Grade": user_info.get("grade", ""),
                 "RAZ Level": user_info.get("raz_level", ""), "Country": user_info.get("country", ""),
                 "State/Province": user_info.get("state", ""), "City": user_info.get("city", ""),
                 "Time Zone": user_info.get("timezone", "")})
        elif isinstance(user_info, str):
            students_list.append(
                {"Encrypted ID": user_id, "Name": user_info, "Grade": "", "RAZ Level": "", "Country": "",
                 "State/Province": "", "City": "", "Time Zone": ""})
    students_df = pd.DataFrame(students_list) if students_list else pd.DataFrame(
        columns=["Encrypted ID", "Name", "Grade", "RAZ Level", "Country", "State/Province", "City"])
    edited_students_df = st.data_editor(students_df, num_rows="dynamic", key="student_editor", use_container_width=True,
                                        column_config={"Encrypted ID": st.column_config.TextColumn(disabled=True),
                                                       "Name": st.column_config.TextColumn(required=True),
                                                       "Grade": st.column_config.TextColumn(),
                                                       "RAZ Level": st.column_config.TextColumn(),
                                                       "Country": st.column_config.TextColumn("Country Key"),
                                                       "State/Province": st.column_config.TextColumn("State/Prov Key"),
                                                       "City": st.column_config.TextColumn("City Key"),
                                                       "Time Zone": st.column_config.TextColumn("Timezone Key")},
                                        column_order=["Encrypted ID", "Name", "Grade", "RAZ Level", "Country",
                                                      "State/Province", "City", "Time Zone"])
    with st.expander("Time Zones:"):
        st.dataframe({"Time Zones": avtimezones})
    # Handle saving changes for students
    if st.button(admin_lang["save_students_button"]):
        original_ids = set(students_df["Encrypted ID"])
        edited_ids = set(edited_students_df["Encrypted ID"])
        deleted_ids = original_ids - edited_ids  # These are the IDs to remove from enrollments

        user_db_before_del = temp_user_db_for_edit  # Get names for info message
        deleted_student_names = {info.get("name", "") if isinstance(info, dict) else info for uid, info in
                                 user_db_before_del.items() if uid in deleted_ids and info}

        new_user_database = {};
        error_occurred = False
        # name_changes no longer needed for enrollment updates

        for index, row in edited_students_df.iterrows():
            # ... (Processing each row to build new_user_database - unchanged, includes RAZ) ...
            user_id = row["Encrypted ID"];
            name = row["Name"]
            if pd.isna(name) or str(name).strip() == "": st.error(
                f"Row {index + 1}: Name empty."); error_occurred = True; continue
            if pd.isna(user_id): st.error(f"Row {index + 1}: ID missing."); error_occurred = True; continue
            clean_name = str(name).strip();
            clean_grade = str(row["Grade"]).strip() if pd.notna(row["Grade"]) else "";
            clean_raz = str(row["RAZ Level"]).strip() if pd.notna(row["RAZ Level"]) else "";
            clean_country = str(row["Country"]).strip() if pd.notna(row["Country"]) else "";
            clean_state = str(row["State/Province"]).strip() if pd.notna(row["State/Province"]) else "";
            clean_city = str(row["City"]).strip() if pd.notna(row["City"]) else ""
            new_user_database[user_id] = {"name": clean_name, "grade": clean_grade, "raz_level": clean_raz,
                                          "country": clean_country, "state": clean_state, "city": clean_city,
                                          "timezone": str(row["Time Zone"])}
            # No need to track name_changes for enrollments anymore

        if not error_occurred:
            try:
                save_data(USER_DB_PATH, new_user_database)
                user_database_global = new_user_database
                st.success("Student data updated!")
                valid_deleted_names = {s for s in deleted_student_names if s}
                if valid_deleted_names: st.info(f"Removed students: {', '.join(valid_deleted_names)}")

                # --- Update enrollments: Remove deleted IDs ---
                if deleted_ids:  # Only run if students were actually deleted
                    enrollments_updated = False
                    current_enrollments = load_data(ENROLLMENTS_DB_PATH)  # Load fresh
                    new_enrollments = current_enrollments.copy()

                    for teacher, student_id_list in current_enrollments.items():
                        original_length = len(student_id_list)
                        # Keep only IDs NOT in the deleted_ids set
                        cleaned_id_list = [s_id for s_id in student_id_list if s_id not in deleted_ids]

                        if len(cleaned_id_list) != original_length:
                            enrollments_updated = True
                            if cleaned_id_list:
                                new_enrollments[teacher] = cleaned_id_list
                            # Remove teacher key if list becomes empty
                            elif teacher in new_enrollments:
                                del new_enrollments[teacher]

                    if enrollments_updated:
                        save_data(ENROLLMENTS_DB_PATH, new_enrollments)
                        enrollments_global = new_enrollments  # Update global state
                        st.info("Updated enrollments for deleted students.")
                        # Name change logic is removed as it's no longer needed

                st.rerun()  # Rerun to reflect changes
            except Exception as e:
                st.error(f"Failed to save student data: {e}")
        else:
            st.warning("Fix errors before saving student changes.")

    st.markdown("---")

    # --- Manage Teacher-Student Assignments (READ-ONLY VIEW) ---
    st.subheader(admin_lang["manage_assignments_header"])

    assignments_list_enriched = []
    current_enrollments = load_data(ENROLLMENTS_DB_PATH)  # Load fresh (contains IDs)
    user_db_for_assignments = load_data(USER_DB_PATH)  # Load fresh user data

    # Build the enriched list for the DataFrame
    for teacher, student_id_list in current_enrollments.items():
        print(student_id_list)
        for student_id in student_id_list:

            details = user_db_for_assignments.get(student_id)  # Lookup by ID

            if isinstance(details, dict):  # Found details
                student_name = details.get("name", f"Unknown ID: {student_id}")
                location_str = f"{details.get('city', '')}, {details.get('state', '')}, {details.get('country', '')}".strip(
                    ", ")
                print(teacher)
                assignments_list_enriched.append({
                    "Teacher": teachers_database_global[teacher]["name"],
                    "Student": student_name,  # Display name
                    "Grade": details.get("grade", ""),
                    admin_lang["raz_level_column"]: details.get("raz_level", ""),
                    admin_lang["location_column"]: location_str if location_str != "," else "",
                    "_Student ID": student_id,
                    "_Teacher ID": teacher
                })
            else:  # Student ID exists in enrollment but not in user_db? Data inconsistency.
                assignments_list_enriched.append({
                    "Teacher": teacher, "Student": f"Missing User Data (ID: {student_id})", "Grade": "N/A",
                    admin_lang["raz_level_column"]: "N/A", admin_lang["location_column"]: "N/A",
                    "_Student ID": student_id,
                    "_Teacher ID": teacher
                })

    # Create DataFrame from the enriched list
    assign_cols = ["Teacher", "Student", "Grade", admin_lang["raz_level_column"], admin_lang["location_column"],
                   "_Student ID", "_Teacher ID"]
    assignments_df = pd.DataFrame(assignments_list_enriched,
                                  columns=assign_cols) if assignments_list_enriched else pd.DataFrame(
        columns=assign_cols)

    #teacher_edit = st.data_editor(assignments_df,key="s-t-assignments",use_container_width=True,num_rows="dynamic")
    # Display the DataFrame as a table (read-only)
    st.dataframe(
        assignments_df,
        column_config={  # Define headers, widths etc. Still useful for display formatting.
            "Teacher": st.column_config.TextColumn(width="medium"),
            "Student": st.column_config.TextColumn(width="medium"),
            "Grade": st.column_config.TextColumn(width="small"),
            admin_lang["raz_level_column"]: st.column_config.TextColumn(width="small"),
            admin_lang["location_column"]: st.column_config.TextColumn(width="large"),
        },
        use_container_width=True,
        hide_index=True,
    )
    add, dele = st.tabs(["Add", "Delete"])
    with add:
        st.write("1. Select A teacher")
        tevent = st.dataframe(
            teachers_df,
            column_config={  # Define headers, widths etc. Still useful for display formatting.
                "Teacher": st.column_config.TextColumn(width="medium"),
                "Student": st.column_config.TextColumn(width="medium"),
                "Grade": st.column_config.TextColumn(width="small"),
                admin_lang["raz_level_column"]: st.column_config.TextColumn(width="small"),
                admin_lang["location_column"]: st.column_config.TextColumn(width="large"),
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="t-add"
        )
        st.write("2. Select Students To Be Enrolled to that Teacher")

        if tevent.selection.rows != []:
            selected_tid = teachers_df.loc[tevent.selection.rows[0], "Teacher ID"]
            print(selected_tid)
            enrolled_students = current_enrollments.get(selected_tid)
            if enrolled_students != None:
                students1_df = students_df[~students_df["Encrypted ID"].isin(enrolled_students)]
            else:
                students1_df = students_df
        else:
            students1_df = []
        event = st.dataframe(
            students1_df,
            column_config={  # Define headers, widths etc. Still useful for display formatting.
                "Teacher": st.column_config.TextColumn(width="medium"),
                "Student": st.column_config.TextColumn(width="medium"),
                "Grade": st.column_config.TextColumn(width="small"),
                admin_lang["raz_level_column"]: st.column_config.TextColumn(width="small"),
                admin_lang["location_column"]: st.column_config.TextColumn(width="large"),
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="add"
        )
        if st.button(admin_lang["save_s-t_button"], key="s-t-ass-add"):

            if (tevent.selection.rows == []):
                st.error("Need to Choose a Teacher")
            elif (event.selection.rows == []):
                st.error("Need to Choose AT LEAST 1 Student")
            else:
                teacherr = teachers_df.loc[tevent.selection.rows[0], "Teacher ID"]
                studentss = students_df.iloc[event.selection.rows]
                enrmts = load_data(ENROLLMENTS_DB_PATH)

                if enrmts.get(teacherr) == None:
                    enrmts[teacherr] = tuple(studentss["Encrypted ID"][:])
                else:
                    enrmts[teacherr] += tuple(studentss["Encrypted ID"][:])
                save_data(ENROLLMENTS_DB_PATH, enrmts)
                st.rerun()
                # enrmts[teacherr]=studentss["Encrypted ID"]

    with dele:
        st.write("1. Select Students to Un-enroll")
        event = st.dataframe(
            assignments_df,
            column_config={  # Define headers, widths etc. Still useful for display formatting.
                "Teacher": st.column_config.TextColumn(width="medium"),
                "Student": st.column_config.TextColumn(width="medium"),
                "Grade": st.column_config.TextColumn(width="small"),
                admin_lang["raz_level_column"]: st.column_config.TextColumn(width="small"),
                admin_lang["location_column"]: st.column_config.TextColumn(width="large"),
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="del"
        )
        if st.button(admin_lang["save_s-t_button"], key="s-t-ass-del"):

            stid = list(assignments_df.loc[event.selection.rows, "_Student ID"])
            tcid = list(assignments_df.loc[event.selection.rows, "_Teacher ID"])
            for teach, stud in zip(tcid, stid):
                del current_enrollments[teach][[i for i, x in enumerate(current_enrollments[teach]) if x == stud][0]]
            save_data(ENROLLMENTS_DB_PATH, current_enrollments)
            st.rerun()
    st.markdown("---")
    st.subheader("Automated Batch Actions (Proceed with Caution)")

    SWITCH = load_data(SWITCH_DB_PATH)

    infos = ""
    dtf = []
    enrinfo = broadcasted_info.get("Open Enrollment", False)
    enrinfo1 = broadcasted_info.get("Close Enrollment", False)
    ratinfo = broadcasted_info.get("Open Ratings", False)
    ratinfo1 = broadcasted_info.get("Close Ratings", False)
    dela= broadcasted_info.get("Open Enrollment Delay", False)

    def _():
        with st.form("Batch Action Form"):
            st.write("**Open Enrollment At (Date):**")

            st.write("**Close Enrollement:**")
            st.write("AFTER Enrollemnt Opened (Days):")

            st.write("At time (Hour:Minute)")

            st.write("**Close Enrollement**")

            st.write("**Open Ratings:**")
            st.write("AFTER Enrollment Closed (Days)")

            st.write("At time (Hour:Minute)")

            st.write("**Close Ratings:**")

            st.write("AFTER Ratings Opened (Days)")

            st.write("At time (Hour:Minute)")
            st.form_submit_button("yo")

    if enrinfo:
        deo = enrinfo[0]
        teo = enrinfo[1]
    else:
        deo = None
        teo = None
    if ratinfo:
        dro = ratinfo[0]
        tro = ratinfo[1]
    else:
        dro = None
        tro = None
    if enrinfo1:
        deo1 = enrinfo1[0]
        teo1 = enrinfo1[1]
    else:
        deo1 = None
        teo1 = None
    if ratinfo1:
        dro1 = ratinfo1[0]
        tro1 = ratinfo1[1]
    else:
        dro1 = None
        tro1 = None
    # edit_schedule = pd.DataFrame([{"Action":"Open Enrollment","Day (Monday, Tuesday, etc.)":deo, "Time (24 Hour Format in Hour:Min)":teo},{"Action":"Close Enrollment","Day (Monday, Tuesday, etc.)":deo1, "Time (24 Hour Format in Hour:Min)":teo1},{"Action":"Open Ratings","Day (Monday, Tuesday, etc.)":dro, "Time (24 Hour Format in Hour:Min)":tro},{"Action":"Close Ratings","Day (Monday, Tuesday, etc.)":dro1, "Time (24 Hour Format in Hour:Min)":tro1}])
    # edited_sched = st.data_editor(edit_schedule,disabled=["Action"],hide_index=True)

    enrange = broadcasted_info.get("Open Enrollment Date")
    enrange1 = broadcasted_info.get("Close Enrollment Date")
    ratrange = broadcasted_info.get("Open Ratings Date")
    ratrange1 = broadcasted_info.get("Close Ratings Date")
    enrd = None
    st.write("Time Range for Enrollment")
    if not enrange:

        #nrd = st.date_input("The Time Range for Enrollment", (datetime.date.today(), datetime.date.today()))
        #tmed = st.text_input("Start Time (in Hours:Minutes)", key="sttrr", value="0:00")
        #tmst = st.text_input("End Time (in Hours:Minutes)", key="edtrr", value="0:00")
        ddate_range_string = date_range_picker(picker_type=PickerType.time,
                                              start=datetime.datetime.now(), end=datetime.datetime.now(),
                                              key='time_range_picker')
        #print(date_range_string)
        if ddate_range_string:
            enrd = [datetime.datetime.strptime(ddate_range_string[0], "%Y-%m-%d %H:%M:%S"),
                datetime.datetime.strptime(ddate_range_string[1], "%Y-%m-%d %H:%M:%S")]
        #print(enrd)
    else:

        #enrd = st.date_input("The Time Range for Enrollment", (datetime.datetime.strptime(enrange,"%Y-%m-%d %H:%M"), datetime.datetime.strptime(enrange1,"%Y-%m-%d %H:%M")))
        #tmed = st.text_input("Start Time (in Hours:Minutes)", key="sttrr", value="0:00")
        #tmst = st.text_input("End Time (in Hours:Minutes)", key="edtrr", value="0:00")

        ddate_range_string = date_range_picker(picker_type=PickerType.time,
                                              start=datetime.datetime.strptime(enrange,"%Y-%m-%d %H:%M").astimezone(st.session_state.timezone_admin), end=datetime.datetime.strptime(enrange1,"%Y-%m-%d %H:%M").astimezone(st.session_state.timezone_admin),
                                              key='time_range_picker')
        #print(date_range_string)
        if ddate_range_string:
            enrd=[datetime.datetime.strptime(ddate_range_string[0],"%Y-%m-%d %H:%M:%S"),datetime.datetime.strptime(ddate_range_string[1],"%Y-%m-%d %H:%M:%S")]
        #print(enrd)
    ratd = None
    st.write("Time Range for Rating (MUST BE AFTER ENROLLMENT CLOSED)")
    print(enrd)
    if not ratrange and enrd and len(enrd) == 2:
        print(enrd)
        #ratd = st.date_input("The Time Range for Rating (Must Be AFTER Enrollment CLOSES)", (enrd[1], enrd[1]))
        #rted = st.text_input("Start Time (in Hours:Minutes)", key="sttrrat", value="0:00")
        #rtst = st.text_input("End Time (in Hours:Minutes)", key="edtrrat", value="0:00")
        date_range_string = date_range_picker(picker_type=PickerType.time,
                                              start=enrd[1], end=enrd[1],
                                              key='time_range_picker1')
        if date_range_string:
            ratd=[datetime.datetime.strptime(date_range_string[0], "%Y-%m-%d %H:%M:%S"),
                datetime.datetime.strptime(date_range_string[1], "%Y-%m-%d %H:%M:%S")]
        print(ratd)
    elif ratrange:
        print(enrd)
        #ratd = st.date_input("The Time Range for Rating (Must Be AFTER Enrollment CLOSES)", (datetime.datetime.strptime(ratrange,"%Y-%m-%d %H:%M"), datetime.datetime.strptime(ratrange1,"%Y-%m-%d %H:%M")))
        #rted = st.text_input("Start Time (in Hours:Minutes)", key="sttrrat", value="0:00")
        #rtst = st.text_input("End Time (in Hours:Minutes)", key="edtrrat", value="0:00")
        date_range_string = date_range_picker(picker_type=PickerType.time,
                                              start=datetime.datetime.strptime(ratrange,"%Y-%m-%d %H:%M").astimezone(st.session_state.timezone_admin), end=datetime.datetime.strptime(ratrange1,"%Y-%m-%d %H:%M").astimezone(st.session_state.timezone_admin),
                                              key='time_range_picker1')
        if date_range_string:
            ratd = [datetime.datetime.strptime(date_range_string[0], "%Y-%m-%d %H:%M:%S"),
                datetime.datetime.strptime(date_range_string[1], "%Y-%m-%d %H:%M:%S")]
        print(ratd)
    st.write("Time Interval Between Ending Rating and Starting new Enrollment:")
    col1, col2, col3 = st.columns(3)
    delt=False
    if dela:
        days,hours,minutes,seconds =  string_to_params(dela)
    with col1:
        if dela:
            days = st.number_input("Days", min_value=0, step=1, value=days)
        else:
            days = st.number_input("Days", min_value=0, step=1, value=3)

    with col2:
        if dela:
            hours = st.number_input("Hours", min_value=0, max_value=23, step=1, value=hours)
        else:
            hours = st.number_input("Hours", min_value=0, max_value=23, step=1, value=12)


    with col3:
        if dela:
            minutes = st.number_input("Minutes", min_value=0, max_value=59, step=1, value=minutes)
        else:
            minutes = st.number_input("Minutes", min_value=0, max_value=59, step=1, value=3)

    st.write(f"Current Schedule:")
    #st.info(f"Start Enrollment at {ddate_range_string[0]} and End Enrollment at {ddate_range_string[1]}.")
    #st.info(f"Then, after {(ratd[0]-enrd[1])}, Start Rating at {date_range_string[0]} and End Rating at {date_range_string[1]}.")
    time_delta = datetime.timedelta(days=days, hours=hours, minutes=minutes)
    assign_cols = ["Action", "Time"]
    if ddate_range_string:
        assignments_df = pd.DataFrame([{"Action":"Start Enrollment At", "Time":ddate_range_string[0]},{"Action":"End Enrollment At", "Time":ddate_range_string[1]},{"Action":"Wait For", "Time":str(ratd[0]-enrd[1])},{"Action":"Start Rating At", "Time":date_range_string[0]},{"Action":"End Rating At", "Time":date_range_string[1]},{"Action":"Repeat Schedult After", "Time":str(time_delta)}],
                                      columns=assign_cols) if assignments_list_enriched else pd.DataFrame(
            columns=assign_cols)
        st.dataframe(
            assignments_df,
            column_config={  # Define headers, widths etc. Still useful for display formatting.
                "Action": st.column_config.TextColumn(width="medium"),
                "Time": st.column_config.TextColumn(width="medium"),

            },
            use_container_width=True,
            hide_index=True,
        )


    save_sched = st.button("Save Schedule", key="save_sc")
    if save_sched:

        cpld = {}
        erred = False
        notsameday = False
        notsametime = False
        now = datetime.datetime.now()
        # print(find_date(current_year,currdatetime.datetime.combine(find_date_of_day_in_current_week(cpld[m][0],datetime.date.today()), datetime.datetime.strptime(cpld[m][1], "%H:%M").time()).strftime("%Y-%m-%d %H:%M")ent_month,current_week, ))
        if ratd[0] < enrd[1]:
            print(ratd, enrd)
            st.error("The Time Range for Rating Must Be AFTER the date the Enrollment CLOSES")
        else:
            if enrd != None:
                SWITCH["Open Enrollment Date"] = enrd[0].astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")#datetime.datetime.combine(enrd[0], datetime.datetime.strptime(tmed,"%H:%M").time()).astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
                SWITCH["Close Enrollment Date"] = enrd[1].astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")#datetime.datetime.combine(enrd[1], datetime.datetime.strptime(tmst,"%H:%M").time()).astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
            if ratd != None:
                SWITCH["Open Ratings Date"] = ratd[0].astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")#datetime.datetime.combine(ratd[0], datetime.datetime.strptime(rted,"%H:%M").time()).astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
                SWITCH["Close Ratings Date"] = ratd[1].astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")#datetime.datetime.combine(ratd[1], datetime.datetime.strptime(rtst,"%H:%M").time()).astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")

            SWITCH["Open Enrollment Delay"]=str(time_delta)
            print(SWITCH)
            save_data(SWITCH_DB_PATH, SWITCH)
            st.rerun()
    st.markdown("---")

    st.subheader("Manual Batch Actions (Proceed with Caution)")

    all_rate = SWITCH["rating"]
    all_hidden = SWITCH["all_hidden"]
    all_closed = SWITCH["all_closed"]
    teaches = load_data(TEACHERS_DB_PATH)
    if all_hidden:
        st.info("All Classes set to Hidden")
        hide_all_classes = st.button("Show All Classes", key="hide_all")
    else:
        st.info("All Classes set to Shown")
        hide_all_classes = st.button("Hide All Classes", key="hide_all")
    if all_closed:
        st.info("Enrollments Closed for All")
        close_all_enroll = st.button("Open Enrollment for All Classes", key="close_all")
    else:
        st.info("Enrollments Opened for All")
        close_all_enroll = st.button("Close Enrollment for All Classes", key="close_all")
    if all_rate:
        st.info("Ratings Enabled for All")
        rate_all = st.button("Disable Rating for All Students", key="rate_all")
    else:
        st.info("Ratings Closed for All")
        rate_all = st.button("Enable Rating for All Student", key="rate_all")

    if hide_all_classes:
        if all_hidden:
            SWITCH["all_hidden"] = False
            for info in teaches:
                teaches[info]["is_active"] = True
        else:
            SWITCH["all_hidden"] = True
            for info in teaches:
                teaches[info]["is_active"] = False
        save_data(TEACHERS_DB_PATH, teaches)
        save_data(SWITCH_DB_PATH, SWITCH)
        st.rerun()

    if close_all_enroll:

        if all_closed:
            SWITCH["all_closed"] = False
            for info in teaches:
                teaches[info]["allow_enroll"] = True
        else:
            SWITCH["all_closed"] = True
            for info in teaches:
                teaches[info]["allow_enroll"] = False
        save_data(TEACHERS_DB_PATH, teaches)
        save_data(SWITCH_DB_PATH, SWITCH)
        print(SWITCH)
        st.rerun()

    if rate_all:

        all_rate = SWITCH["rating"]
        if all_rate:
            SWITCH["rating"] = False


        else:
            SWITCH["rating"] = True
        save_data(SWITCH_DB_PATH, SWITCH)
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
        if not entered_id:
            st.warning("Please enter ID.")
        else:

            current_teachers_db = load_data(TEACHERS_DB_PATH)
            teacher_det = current_teachers_db.get(entered_id)  # Uses validate_teacher_id
            teacher_name = teacher_det.get("name")
            if teacher_det and teacher_name:
                # Set session state
                st.session_state.teacher_logged_in = True
                st.session_state.teacher_id = entered_id
                st.session_state.teacher_name = teacher_name
                st.success(f"Welcome, {teacher_name}!")
                # Rerun will now hit the routing logic which will call teacher_dashboard directly
                st.rerun()
            else:
                st.error("Invalid Teacher ID.")
def sanitize_user_id_for_folder(user_id):
    """Sanitizes the user ID to create a safe folder name."""
    if not user_id:
        return ""
    # This sanitization MUST be identical to the one in your uploader app
    safe_name = "".join(c for c in user_id if c.isalnum() or c in ('_', '-')).rstrip()
    return safe_name
def find_user_file(user_id):
    """
    Finds the uploaded file for a given user_id.
    Returns (file_path, filename, error_message).
    """
    if not user_id:
        return None, None, "User ID cannot be empty."

    safe_user_folder_name = sanitize_user_id_for_folder(user_id)
    if not safe_user_folder_name:
        return None, None, "User ID resulted in an invalid folder name."

    user_specific_dir = os.path.join(BASE_UPLOAD_DIRECTORY, safe_user_folder_name)

    if not os.path.exists(user_specific_dir) or not os.path.isdir(user_specific_dir):
        return None, None, f"No uploads found for User ID '{user_id}'. Directory does not exist."

    # List files in the user's directory
    try:
        files_in_dir = [f for f in os.listdir(user_specific_dir) if os.path.isfile(os.path.join(user_specific_dir, f))]
    except Exception as e:
        return None, None, f"Error accessing directory for User ID '{user_id}': {e}"

    if not files_in_dir:
        return None, None, f"No file found in the directory for User ID '{user_id}'."

    # Assuming only one file per user as per previous uploader logic
    filename = files_in_dir[0]
    file_path = os.path.join(user_specific_dir, filename)

    return file_path, filename, None
def teacher_register():
    lang=texts["English"]
    registration_successful = st.session_state.get("teacher_registration_done", False)  # Flag
    #print(registration_successful)
    if not registration_successful:  # Only show registration form if not yet done
        st.write(lang["teach_reg_p"])
        new_teach_name = st.text_input(lang["reg_name_t"], key="teach_name")
        new_teach_grade = st.text_input(lang["reg_g_t"], key="teach_grade")
        new_teach_course = st.text_input(lang["reg_c_t"], key="teach_course")
        new_teach_desc = st.text_area(lang["reg_desc"], key="teach_desc")
        st.write(lang["autcompl"])

        location_data = streamlit_geolocation()  # Use a unique key

        if location_data and 'latitude' in location_data and 'longitude' in location_data:
            latitude = location_data.get('latitude')
            longitude = location_data.get('longitude')

            if latitude is not None and longitude is not None:

                # Initialize TimezoneFinder
                # This object can be computationally expensive to create,
                # so for performance in a real app, you might consider caching it
                # or creating it once at the start of the script if not using Streamlit's rerun magic.
                # However, for this simple case, direct initialization is fine.
                tf = TimezoneFinder()

                # Get the timezone string
                # Note: timezone_at() expects longitude first, then latitude
                timezone_str = tf.timezone_at(lng=longitude, lat=latitude)

                if timezone_str:
                    if "timezone_teach" not in st.session_state:
                        st.session_state.timezone_teach = pytz.timezone(timezone_str)
                    timzs = [None,timezone_str] + avtimezones
                    selected_zone = st.selectbox(lang["selectzone"], options=timzs, key="timezone12",index=1)

            else:
                selected_zone = st.selectbox(lang["selectzone"], options=[None] + avtimezones, key="timezonet12")
        st.markdown("---")
        params = st.query_params
        current_eid_from_new_api = params.get("eid", [None])[0]
        #st.write(f"Using `st.query_params`: Current `eid` = `{current_eid_from_new_api}`")
        #st.write(f"All params (new API): `{params.to_dict()}`")
        if st.button(lang["register_button"], key="register_btnt"):
            teach_datab=load_data(TEACHERS_DB_PATH)
            if new_teach_name.strip() and new_teach_grade and new_teach_course:
                teach_data_to_save = {"name": new_teach_name,
                                        "subject_en": new_teach_course,
                                        "grade": new_teach_grade,
                                        "description_en": new_teach_desc,
                                        "description_zh": "",
                                        "is_active": True,
                                        "allow_enroll": True,
                                        "enrollment_cap": None,
                                        "rated": {},
                                        "rating": None,
                                        "timezone": selected_zone}
                ntid=generate_teacher_id()
                teach_datab[ntid] = teach_data_to_save
                save_data(TEACHERS_DB_PATH, teach_datab)
                st.session_state.teacher_registration_done = True
                st.session_state.new_teacher_id = ntid  # Store ntid if needed later
                st.rerun()  # Rerun to reflect success and show next step
                #st.success(lang["registered_success"].format(name=new_teach_name.strip()))
                #st.balloons()
    else:
        st.success(lang["registered_success"].format(name="New Teacher"))  # Or use saved name
        st.info("Your ID (copy and keep it somewhere safe...): ")
        st.code(st.session_state.get("new_teacher_id", "Error retrieving ID"))

        st.markdown("---")

        if st.button("Go to Teacher Login", key="go_to_teacher_login_after_reg"):
            st.query_params.eid = "teacher"
            st.rerun()

    #st.stop()
# --- Main Application Logic ---
params = st.query_params
plain_id = params.get("eid", "");
plain_id = plain_id[0] if isinstance(plain_id, list) else plain_id
if not plain_id: st.error("No user id provided (?eid=...)"); st.stop()
if "request_id" not in st.session_state:
    st.session_state.request_id = plain_id.lower()
elif st.session_state.request_id != plain_id:
    st.session_state.request_id = plain_id.lower()

request_id=st.session_state.request_id
# --- Routing ---
if request_id == "admin":
    _ = admin_route()  # Assign return value to _ to potentially suppress output

elif request_id == "teacher":
    if st.session_state.get("teacher_logged_in"):
        _ = teacher_dashboard()  # Assign return value to _
    else:
        _ = teacher_login_page()  # Assign return value to _
elif request_id == "teach_reg":
    teacher_register()

elif:

    selected_language = st.sidebar.selectbox(
        texts["English"]["language_label"] + " / " + texts["中文"]["language_label"], options=["English", "中文"],
        key="lang_select")
    lang = texts.get(selected_language, texts["English"])
    lang_code = 'en' if selected_language == 'English' else 'zh-cn'
    secure_id = request_id  # The unique ID for the current user

    st.markdown(f"""<script>document.title = "{lang['page_title']}";</script>""", unsafe_allow_html=True)



    # Load necessary data
    user_database = load_data(USER_DB_PATH)
    teachers_database = load_data(TEACHERS_DB_PATH)
    enrollments = load_data(ENROLLMENTS_DB_PATH)  # Contains {teacher: [student_id,...]}

    # --- REGISTRATION Section (Unchanged) ---
    if secure_id not in user_database:
        # ... (Registration code remains the same - saves name, grade, raz, location keyed by secure_id) ...
        st.title(lang["page_title"]);
        st.write(lang["register_prompt"])
        new_user_name = st.text_input(lang["register_name_label"], key="reg_name")
        new_user_grade = st.text_input(lang["register_grade_label"], key="reg_grade")
        new_user_raz = st.text_input(lang["register_raz_label"], key="reg_raz")
        st.write(lang["autcompl"])

        location_dat = streamlit_geolocation()  # Use a unique key
        if location_dat and 'latitude' in location_dat and 'longitude' in location_dat:
            latitude = location_dat.get('latitude')
            longitude = location_dat.get('longitude')

            if latitude is not None and longitude is not None:

                # --- Timezone ---
                tf = TimezoneFinder()
                timezone_str = tf.timezone_at(lng=longitude, lat=latitude)
                if timezone_str:
                    try:
                        user_timezone = pytz.timezone(timezone_str)
                        time_in_timezone = datetime.datetime.now(user_timezone)
                    except Exception as e:
                        st.error(f"Error getting current time for timezone: {e}")
                else:
                    st.warning("Could not determine the timezone for the given coordinates.")

                try:
                    results = rg.search((latitude, longitude))  # Returns a list of ordered dicts
                    if results:

                        location_info = results[0]
                        city = location_info.get('name')
                        country_code = location_info.get('cc')
                        state_province = location_info.get('admin1')  # e.g., State in US, Province in Canada

                        country_name = "Unknown"
                        if country_code:
                            try:
                                country_obj = pycountry.countries.get(alpha_2=country_code)
                                if country_obj:
                                    country_name = country_obj.name
                            except Exception as e:
                                st.warning(f"Could not convert country code '{country_code}' to name: {e}")

                        country_options = [lang["select_country"],country_name] + sorted(location_data.keys());
                        selected_country = st.selectbox(lang["register_country_label"], options=country_options,
                                                        key="reg_country",
                                                        index=1)
                        state_options = [lang["select_state"],state_province];
                        if selected_country != lang[
                            "select_country"] and selected_country in location_data: state_options.extend(
                            sorted(location_data[selected_country].keys()))
                        selected_state = st.selectbox(lang["register_state_label"], options=state_options,
                                                      key="reg_state", index=1,
                                                      disabled=(selected_country == lang["select_country"]), )
                        city_options = [lang["select_city"], city];
                        if selected_state != lang[
                            "select_state"] and selected_country in location_data and selected_state in \
                                location_data[selected_country]: city_options.extend(
                            sorted(location_data[selected_country][selected_state]))
                        selected_city = st.selectbox(lang["register_city_label"], options=city_options, key="reg_city",
                                                     index=1,
                                                     disabled=(selected_state == lang["select_state"]))
                        print(timezone_str)
                        timzs=[None,timezone_str] + avtimezones
                        print(timzs)
                        selected_zone = st.selectbox(lang["selectzone"], options=timzs, key="timezonet",index=1)


                    else:
                        st.warning("Could not find location details using reverse_geocoder.")
                except Exception as e:
                    st.error(f"Error during reverse geocoding with reverse_geocoder: {e}")

            else:

                country_options = [lang["select_country"]] + sorted(location_data.keys());
                selected_country = st.selectbox(lang["register_country_label"], options=country_options, key="reg_country",
                                                index=0)
                state_options = [lang["select_state"]];
                if selected_country != lang["select_country"] and selected_country in location_data: state_options.extend(
                    sorted(location_data[selected_country].keys()))
                selected_state = st.selectbox(lang["register_state_label"], options=state_options, key="reg_state", index=0,
                                              disabled=(selected_country == lang["select_country"]),)
                city_options = [lang["select_city"]];
                if selected_state != lang["select_state"] and selected_country in location_data and selected_state in \
                        location_data[selected_country]: city_options.extend(
                    sorted(location_data[selected_country][selected_state]))
                selected_city = st.selectbox(lang["register_city_label"], options=city_options, key="reg_city", index=0,
                                             disabled=(selected_state == lang["select_state"]))
                selected_zone = st.selectbox(lang["selectzone"], options=[None] + avtimezones, key="timezone")
        st.markdown("---")
        if st.button(lang["register_button"], key="register_btn"):
            print(selected_zone, selected_country, selected_state, selected_city)

            if new_user_name.strip() and new_user_raz and selected_zone and selected_country != lang[
                "select_country"] and selected_state != lang["select_state"] and selected_city != lang["select_city"]:
                user_data_to_save = {"name": new_user_name.strip(), "grade": new_user_grade.strip(),
                                     "raz_level": new_user_raz.strip(), "country": selected_country,
                                     "state": selected_state, "city": selected_city, "timezone": selected_zone}
                user_database[secure_id] = user_data_to_save
                save_data(USER_DB_PATH, user_database);
                user_database_global = user_database
                st.success(lang["registered_success"].format(name=new_user_name.strip()));
                st.balloons();
                time.sleep(1);
                st.rerun()
            else:
                st.error(lang["fill_all_fields"])
        st.stop()

    enrinfo = broadcasted_info.get("Open Enrollment", False)
    enrinfo1 = broadcasted_info.get("Close Enrollment", False)
    ratinfo = broadcasted_info.get("Open Ratings", False)
    ratinfo1 = broadcasted_info.get("Close Ratings", False)
    if user_database.get(secure_id):
        usrcnt = user_database[secure_id]["timezone"]
    else:
        usrcnt= "UTC"
    enrange = broadcasted_info.get("Open Enrollment Date")
    enrange1 = broadcasted_info.get("Close Enrollment Date")
    ratrange = broadcasted_info.get("Open Ratings Date")
    ratrange1 = broadcasted_info.get("Close Ratings Date")
    dely = broadcasted_info.get("Open Enrollment Delay")
    if enrange and enrange1:
        source_dt = datetime.datetime.now().replace(tzinfo=ZoneInfo("UTC"))
        converted_dt = source_dt.astimezone(ZoneInfo(usrcnt))
        enrange = datetime.datetime.strptime(enrange, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(usrcnt))
        enrange1 = datetime.datetime.strptime(enrange1, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(usrcnt))
        intime = enrange <= converted_dt <= enrange1

        if broadcasted_info["all_closed"] and intime:
            print("wh")
            broadcasted_info["all_closed"] = False
            for info in teachers_database_global:
                teachers_database_global[info]["allow_enroll"] = True
            save_data(SWITCH_DB_PATH, broadcasted_info)
            save_data(TEACHERS_DB_PATH, teachers_database_global)

            st.rerun()

        elif (not broadcasted_info["all_closed"]) and (not intime):
            broadcasted_info["all_closed"] = True
            print("wh1")
            for info in teachers_database_global:
                teachers_database_global[info]["allow_enroll"] = False
            save_data(SWITCH_DB_PATH, broadcasted_info)
            save_data(TEACHERS_DB_PATH, teachers_database_global)
            st.rerun()
    if ratrange and ratrange1:
        source_dt = datetime.datetime.now().replace(tzinfo=ZoneInfo("UTC"))
        converted_dt = source_dt.astimezone(ZoneInfo(usrcnt))
        ratrange = datetime.datetime.strptime(ratrange, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(usrcnt))
        ratrange1 = datetime.datetime.strptime(ratrange1, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(usrcnt))
        intime = ratrange <= converted_dt <= ratrange1
        print(ratrange,ratrange1)
        if (not broadcasted_info["rating"]) and intime:
            print("wh")
            broadcasted_info["rating"] = True
            save_data(SWITCH_DB_PATH, broadcasted_info)
            st.rerun()

        elif (broadcasted_info["rating"]) and not intime:
            print("w1h")
            broadcasted_info["rating"] = False
            save_data(SWITCH_DB_PATH, broadcasted_info)
            st.rerun()
    if enrange and ratrange1 and dely:
        source_dt = datetime.datetime.now().replace(tzinfo=ZoneInfo("UTC"))
        converted_dt = source_dt.astimezone(ZoneInfo(usrcnt))
        inwtime = enrange <= converted_dt <= ratrange1
        outwtime = converted_dt >= ratrange1+string_to_delta(dely)
        if not inwtime and outwtime:
            ste = converted_dt
            ende = ste+(enrange1-enrange)
            ord1 = ende+(ratrange-enrange1)
            cr = ord1+(ratrange1-ratrange)
            broadcasted_info["Open Enrollment Date"]=ste.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M")
            broadcasted_info["Close Enrollment Date"] = ende.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M")
            broadcasted_info["Open Ratings Date"] = ord1.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M")
            broadcasted_info["Close Ratings Date"] = cr.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M")
            save_data(SWITCH_DB_PATH, broadcasted_info)
            st.rerun()


    # --- MAIN ENROLLMENT Section ---
    user_info = user_database.get(secure_id)  # Get current user's details
    if isinstance(user_info, dict):
        user_name = user_info.get("name", f"Unknown ({secure_id})")  # Display name but use ID internally
    # Handle old format if necessary, though less likely now
    elif isinstance(user_info, str):
        user_name = f"{user_info} ({secure_id})"
    else:
        user_name = f"Unknown ({secure_id})"; st.sidebar.error("User data error.")

    # ... (Sidebar display - unchanged) ...
    st.sidebar.write(lang["logged_in"].format(name=user_name))  # Display name
    if isinstance(user_info, dict):
        c, s, ci, gr, rz = user_info.get("country"), user_info.get("state"), user_info.get("city"), user_info.get(
            "grade"), user_info.get("raz_level")
        loc_str = f"{ci}, {s}, {c}" if c and s and ci else "";
        details_str = f"Grade: {gr}" if gr else "";
        if rz: details_str += f" | RAZ: {rz}"
        if loc_str: st.sidebar.caption(loc_str);
        if details_str: st.sidebar.caption(details_str)
    SWITCH = load_data(SWITCH_DB_PATH)
    all_rate = SWITCH["rating"]
    if not all_rate:
        st.title(lang["page_title"])
        if st.sidebar.button(lang["refresh"]): st.rerun()

        # --- Teacher Search and Filter (Unchanged) ---
        # ... (Search/Filter logic remains the same) ...
        st.subheader(lang["teacher_search_label"]);
        col_search, col_grade_filter = st.columns([3, 2])
        with col_search:
            teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter",
                                           label_visibility="collapsed")

        active_teachers = {}
        for n, i in teachers_database.items():
            if i.get("is_active", True):
                active_teachers[n] = i
        unique_grades = sorted(list(
            {str(i.get("grade", "")).strip() for i in active_teachers.values() if str(i.get("grade", "")).strip()}))

        grade_options = [lang["all_grades"]] + unique_grades
        with col_grade_filter:
            selected_grade_filter = st.selectbox(lang["grade_select_label"], options=grade_options, key="grade_select")
        filtered_teachers = {};
        if active_teachers:
            term = teacher_filter.strip().lower()

            for n, i in active_teachers.items():

                name_match = (not term) or (term in n.lower())

                grade_match = (selected_grade_filter == lang["all_grades"]) or (
                            str(i.get("grade", "")).strip() == selected_grade_filter)

                if name_match and grade_match:
                    filtered_teachers[n] = i

        st.markdown("---")

        # --- Display Teachers (Using secure_id for checks/actions) ---
        if not active_teachers:
            st.warning(lang["no_teachers_available"])
        elif not filtered_teachers:
            st.error(lang["teacher_not_found_error"])
        else:

            for teacher_name, teacher_info in filtered_teachers.items():

                st.subheader(teachers_database[teacher_name]["name"])

                # ... (Class Status display and buttons - unch
                # ... (Display Subject/Grade/Description - unchanged) ...
                subject_en = teacher_info.get("subject_en", "N/A");
                display_subject = subject_en
                grade = teacher_info.get("grade", "N/A");
                desc_parts = [];
                if display_subject != "N/A": desc_parts.append(f"**{display_subject}**")
                if grade != "N/A": desc_parts.append(f"({lang['to_grade']} **{grade}**)")
                st.write(f"{lang['teaches']} {' '.join(desc_parts)}" if desc_parts else f"({lang['teaches']} N/A)")
                desc_en = teacher_info.get("description_en", "");
                desc_zh = teacher_info.get("description_zh", "");
                display_desc = desc_zh if selected_language == "中文" and desc_zh else desc_en
                if display_desc:
                    st.markdown(f"> _{display_desc}_")
                else:
                    st.caption(f"_{lang['no_description_available']}_")
                ratt = teacher_info.get("rating", None)
                if (ratt != None and ratt.isdigit() and int(ratt) >= 0):
                    st_star_rating(label=lang["class_rating"], maxValue=5,
                                   defaultValue=int(teacher_info.get("rating", "0")), read_only=True)
                else:
                    st.subheader(lang["class_rating"])
                    st.info(lang["class_no_rating"])
                # --- Enrollment status/buttons (Using secure_id) ---

                current_teacher_enrollment_ids = enrollments.get(teacher_name, [])  # Get list of IDs
                count = len(current_teacher_enrollment_ids)
                cap = teacher_info.get("enrollment_cap");
                cap_text = lang["unlimited"] if cap is None else str(cap)
                is_full = False if cap is None else count >= cap

                # Check enrollment based on the current user's secure_id

                is_enrolled = secure_id in current_teacher_enrollment_ids
                all_enr = teacher_info.get("allow_enroll")
                st.caption(lang["user_enrollment_caption"].format(count=count, cap=cap_text))
                col1, col2 = st.columns(2)
                if not all_enr:
                    st.error(lang["enrollment_closed"])
                with col1:
                    enroll_label = lang["enroll_button"]
                    if is_full:
                        enroll_label = lang["enrollment_full"]
                    elif is_enrolled:
                        enroll_label = lang["enroll_button"]

                    enroll_disabled = is_enrolled or is_full or SWITCH["all_closed"]
                    enroll_clicked = st.button(enroll_label, key=f"enroll_{teacher_name}_{secure_id}",
                                               disabled=enroll_disabled, use_container_width=True)  # Key uses secure_id
                with col2:
                    print(f"yoo:{is_enrolled}")
                    cancel_clicked = st.button(lang["cancel_button"], key=f"cancel_{teacher_name}_{secure_id}",
                                               disabled=not is_enrolled or SWITCH["all_closed"],
                                               use_container_width=True)  # Key uses secure_id
                SWITCH = load_data(SWITCH_DB_PATH)
                all_c = SWITCH["all_closed"]
                all_h = SWITCH["all_hidden"]
                all_r = SWITCH["rating"]
                # --- Button Actions (Using secure_id) ---
                if enroll_clicked:
                    if all_c or all_h or all_r:
                        print("wh")
                        st.rerun()
                    # Re-check conditions on click, use secure_id
                    enrollments_now = load_data(ENROLLMENTS_DB_PATH)  # Load fresh
                    print(f"huh:{teacher_name}")
                    teacher_id_list_now = enrollments_now.get(teacher_name, [])
                    teacher_info_now = load_data(TEACHERS_DB_PATH).get(teacher_name, {})
                    cap_now = teacher_info_now.get("enrollment_cap")
                    is_full_now = False if cap_now is None else len(teacher_id_list_now) >= cap_now

                    if secure_id not in teacher_id_list_now and not is_full_now:
                        teacher_id_list_now.append(secure_id)  # <-- Add secure_id
                        enrollments_now[teacher_name] = teacher_id_list_now
                        save_data(ENROLLMENTS_DB_PATH, enrollments_now)

                        enrollments_global = enrollments_now  # Update global state if needed
                        st.success(lang["enroll_success"].format(name=user_name,
                                                                 teacher=teachers_database[teacher_name]["name"]))
                        st.rerun()
                    # No explicit else needed for already enrolled/full, button is disabled

                if cancel_clicked:

                    if all_c or all_h or all_r:
                        print("wh")
                        st.rerun()

                    # Use secure_id for removal
                    enrollments_now = load_data(ENROLLMENTS_DB_PATH)  # Load fresh

                    if teacher_name in enrollments_now and secure_id in enrollments_now[teacher_name]:

                        enrollments_now[teacher_name].remove(secure_id)  # <-- Remove secure_id
                        if not enrollments_now[teacher_name]:  # Remove teacher key if list empty
                            del enrollments_now[teacher_name]
                        save_data(ENROLLMENTS_DB_PATH, enrollments_now)
                        enrollments_global = enrollments_now  # Update global state if needed
                        st.info(lang["enrollment_cancelled"])
                        st.rerun()
                    # No explicit else needed, button disabled if not enrolled

                # --- Enrollment List Expander (Display names from IDs) ---
                with st.expander(f"{lang['enrolled_label']} ({count})"):
                    if current_teacher_enrollment_ids:
                        # Create list of names to display
                        display_names = []
                        for s_id in current_teacher_enrollment_ids:
                            s_info = user_database.get(s_id)  # Use already loaded user_database
                            s_name_display = f"Unknown ID ({s_id})"  # Default
                            if isinstance(s_info, dict):
                                s_name_display = s_info.get("name", s_name_display)
                            elif isinstance(s_info, str):  # Old format
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
                file_path, filename, error = find_user_file(teacher_name)
                if error:
                    st.info("No Courseware For this Teacher")
                elif file_path and filename:
                    with open(file_path, "rb") as fp:
                        file_bytes = fp.read()

                    # Guess MIME type
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type is None:
                        mime_type = "application/octet-stream"  # Default if unknown
                    st.download_button(
                        label=f"Download Courseware",
                        data=file_bytes,
                        file_name=filename,
                        mime=mime_type,
                        key=f"download_btn_{filename}"
                    )
                st.markdown("---")  # Separator between teachers
    else:
        st.title(lang["page_title_rate"])
        if st.sidebar.button(lang["refresh"]): st.rerun()
        # --- Teacher Search and Filter (Unchanged) ---
        # ... (Search/Filter logic remains the same) ...
        st.subheader(lang["teacher_search_label"]);
        col_search, col_grade_filter = st.columns([3, 2])
        with col_search:
            teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter",
                                           label_visibility="collapsed")
        active_teachers1 = {n: i for n, i in teachers_database.items() if i.get("is_active", True)}
        active_teachers = {}
        for n in active_teachers1:
            print(n)
            if enrollments.get(n, False) and (secure_id in enrollments[n]):
                active_teachers[n] = active_teachers1[n]
        unique_grades = sorted(list(
            {str(i.get("grade", "")).strip() for i in active_teachers.values() if str(i.get("grade", "")).strip()}))
        grade_options = [lang["all_grades"]] + unique_grades
        with col_grade_filter:
            selected_grade_filter = st.selectbox(lang["grade_select_label"], options=grade_options, key="grade_select")
        filtered_teachers = {};
        if active_teachers:
            term = teacher_filter.strip().lower()
            for n, i in active_teachers.items():
                name_match = (not term) or (term in n.lower())
                grade_match = (selected_grade_filter == lang["all_grades"]) or (
                            str(i.get("grade", "")).strip() == selected_grade_filter);

                if name_match and grade_match:
                    filtered_teachers[n] = i
        st.markdown("---")

        # --- Display Teachers (Using secure_id for checks/actions) ---
        if not active_teachers:
            st.warning(lang["no_teachers_rating_available"])
        elif not filtered_teachers:
            st.error(lang["teacher_not_found_error"])
        else:

            for teacher_name, teacher_info in filtered_teachers.items():

                st.subheader(teachers_database[teacher_name]["name"])

                # ... (Class Status display and buttons - unch
                # ... (Display Subject/Grade/Description - unchanged) ...
                subject_en = teacher_info.get("subject_en", "N/A");
                display_subject = subject_en

                grade = teacher_info.get("grade", "N/A");
                desc_parts = [];
                if display_subject != "N/A": desc_parts.append(f"**{display_subject}**")
                if grade != "N/A": desc_parts.append(f"({lang['to_grade']} **{grade}**)")
                st.write(f"{lang['teaches']} {' '.join(desc_parts)}" if desc_parts else f"({lang['teaches']} N/A)")
                desc_en = teacher_info.get("description_en", "");
                desc_zh = teacher_info.get("description_zh", "");
                display_desc = desc_zh if selected_language == "中文" and desc_zh else desc_en
                if display_desc:
                    st.markdown(f"> _{display_desc}_")
                else:
                    st.caption(f"_{lang['no_description_available']}_")
                ratt = teacher_info.get("rating", None)
                with st.form(teacher_name):
                    SWITCH = load_data(SWITCH_DB_PATH)
                    all_c = SWITCH["all_closed"]
                    all_h = SWITCH["all_hidden"]
                    all_r = SWITCH["rating"]
                    start_t = SWITCH["Open Ratings Date"]
                    end_t = SWITCH["Close Ratings Date"]
                    source_dt = datetime.datetime.now().replace(tzinfo=ZoneInfo("UTC"))  # Example: UTC
                    # Convert to the target time zone
                    converted_dt = source_dt.astimezone(ZoneInfo(usrcnt))  # Example: Asia/Shanghai
                    datet = converted_dt.strftime('%Y-%m-%d %H:%M:%S')
                    if (secure_id in teachers_database[teacher_name]["rated"].keys()):
                        st.success(lang["RATED"].format(time=datet))
                        dfv = teachers_database[teacher_name]["rated"][secure_id][-1]["stars"]
                        dfv_txt = teachers_database[teacher_name]["rated"][secure_id][-1]["feedback"]
                    else:
                        dfv_txt = ""
                        dfv = 0
                    rating = st_star_rating(
                        label=lang["rate_class"].format(name=teachers_database[teacher_name]["name"]), maxValue=5,
                        defaultValue=dfv, read_only=False)

                    txt = st.text_area(lang["explanation"].format(name=teachers_database[teacher_name]["name"]),
                                       dfv_txt)
                    btn_form = st.form_submit_button()

                    if btn_form:

                        if (not all_r) or all_h or (not all_c):
                            print("wh")
                            st.rerun()
                        if rating == 0:
                            st.error(lang["ERR_NO_RATE"])
                        else:
                            print("ww")
                            rate_stu = teachers_database[teacher_name]["rated"]

                            if (not rate_stu.get(secure_id, False)):
                                rate_stu[secure_id] = []
                            print(rate_stu)
                            dates = [sub['date'] for sub in rate_stu[secure_id]]
                            print(dates)
                            try:
                                idxd = dates.index(f"{ratrange}-{ratrange1}")
                                rate_stu[secure_id][idxd] = {"date": f"{ratrange}-{ratrange1}", "stars": rating, "feedback": txt}
                            except ValueError:
                                rate_stu[secure_id].append({"date": f"{ratrange}-{ratrange1}", "stars": rating, "feedback": txt})

                            save_data(TEACHERS_DB_PATH, teachers_database)

                            st.rerun()
                file_path, filename, error = find_user_file(teacher_name)
                if error:
                    st.info("No Courseware For this Teacher")
                elif file_path and filename:
                    with open(file_path, "rb") as fp:
                        file_bytes = fp.read()

                    # Guess MIME type
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type is None:
                        mime_type = "application/octet-stream" # Default if unknown
                    st.download_button(
                        label=f"Download Courseware",
                        data=file_bytes,
                        file_name=filename,
                        mime=mime_type,
                        key=f"download_btn_{filename}"
                    )
                st.markdown("---")  # Separator between teachers
