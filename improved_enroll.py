import streamlit as st

# Initialize session state for enrollments if not already set.
if 'enrollments' not in st.session_state:
    st.session_state['enrollments'] = {}

# Define bilingual text labels.
texts = {
    "English": {
        "page_title": "Teacher Search and Enrollment",
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
        "name_required": "No student name provided in the URL. Append '?student=YourName' to your URL for automatic enrollment.",
        "enrolled_label": "Enrolled Students",
        "no_enrollments": "No students enrolled yet.",
        "not_enrolled": "Your name was not found in the enrollment.",
        "logged_in": "Logged in as: {name}"
    },
    "中文": {
        "page_title": "教师搜索与注册",
        "language_label": "选择语言",
        "teacher_search_label": "请输入教师姓名搜索：",
        "teacher_not_found_error": "没有匹配的教师。",
        "enter_teacher_info": "正在显示所有教师。使用上方搜索框筛选。",
        "teaches": "授课",
        "to_grade": "年级",
        "enroll_button": "注册",
        "cancel_button": "取消注册",
        "enroll_success": "谢谢, {name}! 你已注册到 {teacher} 的课程！",
        "enrollment_cancelled": "注册已取消。",
        "name_required": "未在URL中检测到学生姓名。请在URL中添加 '?student=你的名字' 以自动注册。",
        "enrolled_label": "已注册学生",
        "no_enrollments": "当前没有注册学生。",
        "not_enrolled": "未找到你的注册记录。",
        "logged_in": "已登录: {name}"
    }
}

# Sample bilingual teacher data.
teachers = {
    "Alice": {"subject_en": "Mathematics", "subject_zh": "数学", "grade": "8"},
    "Bob": {"subject_en": "Physics", "subject_zh": "物理", "grade": "9"},
    "Charlie": {"subject_en": "History", "subject_zh": "历史", "grade": "10"}
}

# Inject CSS for vertical centering of elements.
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

# Use st.query_params (no longer experimental) to get the student name.
params = st.query_params

# Get the student name without indexing into a string.
student_name = params.get("student", "")
# For backward compatibility, if student_name is a list, grab the first element.
if isinstance(student_name, list):
    student_name = student_name[0]

# Sidebar language selector.
selected_language = st.sidebar.selectbox("Language / 语言", options=["English", "中文"])
lang = texts[selected_language]

# Display logged in student name on the sidebar.
if student_name:
    st.sidebar.write(lang["logged_in"].format(name=student_name))
else:
    st.sidebar.warning(lang["name_required"])

# Set up the page title.
st.title(lang["page_title"])

# Teacher filter input.
teacher_filter = st.text_input(lang["teacher_search_label"], key="teacher_filter")

# Filter the teachers with a case-insensitive match.
filtered_teachers = {
    name: info
    for name, info in teachers.items()
    if teacher_filter.lower() in name.lower()
}

if teacher_filter.strip() == "":
    st.info(lang["enter_teacher_info"])

if not filtered_teachers:
    st.error(lang["teacher_not_found_error"])
else:
    for teacher_name, teacher_info in filtered_teachers.items():
        st.header(teacher_name)

        # Initialize the enrollment list for the teacher if it doesn't exist.
        if teacher_name not in st.session_state['enrollments']:
            st.session_state['enrollments'][teacher_name] = []

        # Display teacher's description.
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

        # Create two columns for the Enroll and Cancel buttons.
        col1, col2 = st.columns(2)
        with col1:
            enroll_clicked = st.button(lang["enroll_button"], key=f"enroll_button_{teacher_name}")
        with col2:
            cancel_clicked = st.button(lang["cancel_button"], key=f"cancel_button_{teacher_name}")

        # Process enrollment if the Enroll button is clicked.
        if enroll_clicked:
            if student_name:
                if student_name not in st.session_state['enrollments'][teacher_name]:
                    st.session_state['enrollments'][teacher_name].append(student_name)
                st.success(lang["enroll_success"].format(name=student_name, teacher=teacher_name))
            else:
                st.error(lang["name_required"])

        # Process cancellation if the Cancel button is clicked.
        if cancel_clicked:
            if student_name and student_name in st.session_state['enrollments'][teacher_name]:
                st.session_state['enrollments'][teacher_name].remove(student_name)
                st.info(lang["enrollment_cancelled"])
            else:
                st.error(lang["not_enrolled"])

        # Display the list of enrolled students inside an expander.
        enrolled_students = st.session_state['enrollments'][teacher_name]
        with st.expander(lang["enrolled_label"]):
            if enrolled_students:
                for s in enrolled_students:
                    st.write(f"- {s}")
            else:
                st.write(lang["no_enrollments"])

        st.markdown("---")
