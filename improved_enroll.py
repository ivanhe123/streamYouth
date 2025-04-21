# Sample location data (replace with actual data or API)
# --- Added more comprehensive sample data ---
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
    # Add more countries, states/provinces, and cities as needed
}

# ... (keep all your existing helper functions, database loading, etc.) ...

# Bilingual Texts - Ensure these keys are present
texts = {
    "English": {
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
        "register_name_label": "Student's English Full Name", # Added for clarity
        "register_grade_label": "Current Grade",
        "register_country_label": "Country",
        "register_state_label": "State/Province",
        "register_city_label": "City",
        "select_country": "--- Select Country ---",         # Updated prompt
        "select_state": "--- Select State/Province ---",   # Updated prompt
        "select_city": "--- Select City ---",              # Updated prompt
        "fill_all_fields": "Please fill in Name and select a valid Country, State/Province, and City." # Added more specific error
    },
    "中文": {
        "page_title": "PLE Youth 教师搜索与注册",
        "language_label": "选择语言",
        "teacher_search_label": "请输入教师姓名搜索：",
        "teacher_not_found_error": "没有匹配的可用教师。",
        "enter_teacher_info": "正在显示所有可用教师。使用上方搜索框筛选。",
        "teaches": "授课",
        "to_grade": "年级",
        "enroll_button": "报名",
        "cancel_button": "取消报名",
        "enroll_success": "谢谢, {name}! 你已注册到 {teacher} 的课程！",
        "enrollment_cancelled": "报名已取消。",
        "register_prompt": "欢迎！请通过输入学生的详细信息完成注册：",
        "register_button": "注册",
        "logged_in": "已登录: {name}",
        "enrolled_label": "已报名的学生",
        "no_enrollments": "当前没有报名的学生。",
        "not_enrolled": "未找到你的报名记录。",
        "name_required": "请输入你的名字以注册。",
        "no_teachers_available": "目前没有可报名的教师。",
        "enrollment_full": "报名已满",
        "user_enrollment_caption": "已报名: {count} / {cap}",
        "unlimited": "无限制",
        "grade_select_label": "选择年级",
        "all_grades": "所有年级",
        "refresh": "刷新",
        "register_name_label": "学生英文全名", # Added for clarity
        "register_grade_label": "当前年级",
        "register_country_label": "国家",
        "register_state_label": "州/省",
        "register_city_label": "城市",
        "select_country": "--- 选择国家 ---",       # Updated prompt
        "select_state": "--- 选择州/省 ---",     # Updated prompt
        "select_city": "--- 选择城市 ---",        # Updated prompt
        "fill_all_fields": "请填写姓名并选择有效的国家、州/省和城市。" # Added more specific error
    }
}


# Main Application Logic
params = st.query_params
plain_id = params.get("id", "")
if isinstance(plain_id, list): plain_id = plain_id[0] if plain_id else ""
if not plain_id:
    st.error("No user id provided. Use ?id=your_id, ?id=admin, or ?id=teacher")
    st.stop()

request_id = plain_id.lower()
if request_id == "admin":
    admin_route()
elif request_id == "teacher":
    teacher_login_page()
else:
    # --- STUDENT/USER PATH ---
    selected_language = st.sidebar.selectbox(
        "Language / 语言",
        options=["English", "中文"],
        key="lang_select",
        # Optional: Add index=0 or 1 based on browser language preference if desired
    )
    lang = texts[selected_language]
    # Use the provided ID directly as the key, encrypt if needed elsewhere but keep it simple for lookup
    secure_id = request_id # Renamed for clarity, no encryption applied here for simplicity
    st.markdown(f"""<script>document.title = "{lang['page_title']}";</script>""", unsafe_allow_html=True)

    # --- Reload data on each run for consistency ---
    user_database = load_data(USER_DB_PATH)
    teachers_database = load_data(TEACHERS_DB_PATH)
    enrollments = load_data(ENROLLMENTS_DB_PATH)

    # --- REGISTRATION Section ---
    if secure_id not in user_database:
        st.title(lang["page_title"])
        st.write(lang["register_prompt"])

        # --- Input fields ---
        new_user_name = st.text_input(lang["register_name_label"], key="register_input")
        new_user_grade = st.text_input(lang["register_grade_label"], key="register_grade")

        # --- Country Dropdown ---
        country_label = lang["register_country_label"]
        select_country_prompt = lang["select_country"]
        # Add a prompt option at the beginning
        country_options = [select_country_prompt] + sorted(list(location_data.keys()))
        selected_country = st.selectbox(
            country_label,
            options=country_options,
            key="register_country",
            index=0 # Default to the prompt
        )

        # --- State/Province Dropdown (Dependent) ---
        state_label = lang["register_state_label"]
        select_state_prompt = lang["select_state"]
        state_options = [select_state_prompt] # Default prompt
        # Check if a valid country (not the prompt) is selected
        if selected_country != select_country_prompt and selected_country in location_data:
            state_options.extend(sorted(list(location_data[selected_country].keys())))

        selected_state = st.selectbox(
            state_label,
            options=state_options,
            key="register_state",
            index=0, # Default to prompt
            disabled=(selected_country == select_country_prompt) # Disable if no valid country selected
        )

        # --- City Dropdown (Dependent) ---
        city_label = lang["register_city_label"]
        select_city_prompt = lang["select_city"]
        city_options = [select_city_prompt] # Default prompt
        # Check if valid country and state (not prompts) are selected
        if selected_country != select_country_prompt and \
           selected_state != select_state_prompt and \
           selected_country in location_data and \
           selected_state in location_data[selected_country]:
            city_options.extend(sorted(location_data[selected_country][selected_state]))

        selected_city = st.selectbox(
            city_label,
            options=city_options,
            key="register_city",
            index=0, # Default to prompt
            disabled=(selected_state == select_state_prompt) # Disable if no valid state selected
        )

        st.markdown("---") # Separator

        # --- Registration Button and Logic ---
        if st.button(lang["register_button"], key="register_btn"):
            # Validate that a real selection was made for all dropdowns and name is present
            if new_user_name and new_user_name.strip() and \
               selected_country != select_country_prompt and \
               selected_state != select_state_prompt and \
               selected_city != select_city_prompt:

                clean_name = new_user_name.strip()
                clean_grade = new_user_grade.strip() if new_user_grade else "" # Grade is optional

                # Prepare user data
                user_data_to_save = {
                    "name": clean_name,
                    "grade": clean_grade,
                    "country": selected_country,
                    "state": selected_state,
                    "city": selected_city
                }
                user_database[secure_id] = user_data_to_save
                save_data(USER_DB_PATH, user_database)

                st.success(f"Registered {clean_name}! Reloading page.")
                st.balloons()
                # Use st.rerun() for a cleaner reload within Streamlit
                st.rerun()
            else:
                # Give a more specific error message
                st.error(lang["fill_all_fields"])
        st.stop() # Stop execution here if user needs to register

    # --- MAIN ENROLLMENT Section (If user is registered) ---
    user_info = user_database.get(secure_id)
    # Handle potential old format where user_info might be just the name string
    if isinstance(user_info, dict):
        user_name = user_info.get("name", "Unknown User")
    elif isinstance(user_info, str):
        user_name = user_info # Old format support
        # Optional: you might want to prompt users with old format to update details
    else:
        user_name = "Unknown User" # Fallback

    st.sidebar.write(lang["logged_in"].format(name=user_name))
    st.title(lang["page_title"])
    if st.sidebar.button(lang["refresh"]): # Moved refresh to sidebar for less clutter
        st.rerun()

    # --- Teacher Search and Filter ---
    st.subheader(lang["teacher_search_label"]) # Use subheader for search section
    col_search, col_grade_filter = st.columns([3, 2]) # Adjust column ratios if needed

    with col_search:
        teacher_filter = st.text_input(
            lang["teacher_search_label"], # Use label param for text_input
            key="teacher_filter",
            label_visibility="collapsed" # Hide label as it's in subheader
        )

    active_teachers = {n: i for n, i in teachers_database.items() if i.get("is_active", True)}
    unique_grades = [""] # Add blank option for grade if needed
    if active_teachers:
         # Ensure grade exists and is not empty before adding
         grades_from_teachers = set(
             str(teacher_info["grade"]).strip()
             for teacher_info in active_teachers.values()
             if "grade" in teacher_info and str(teacher_info.get("grade","")).strip()
         )
         if grades_from_teachers:
              unique_grades = sorted(list(grades_from_teachers))

    grade_options = [lang["all_grades"]] + unique_grades

    with col_grade_filter:
        selected_grade = st.selectbox(
            lang["grade_select_label"],
            options=grade_options,
            key="grade_select"
        )

    # --- Filtering Logic ---
    filtered_teachers = {}
    if active_teachers:
        filter_term = teacher_filter.strip().lower()
        for n, i in active_teachers.items():
            # Check name filter (if exists)
            name_match = (not filter_term) or (filter_term in n.lower())
            # Check grade filter
            grade_match = (selected_grade == lang["all_grades"]) or \
                          (str(i.get("grade", "")).strip() == selected_grade)

            if name_match and grade_match:
                filtered_teachers[n] = i

    st.markdown("---") # Separator

    # --- Display Teachers ---
    if not active_teachers:
        st.warning(lang["no_teachers_available"])
    elif not filtered_teachers:
        st.error(lang["teacher_not_found_error"])
    else:
        # Optional: Show info only if no filters are active
        # if not teacher_filter.strip() and selected_grade == lang["all_grades"]:
        #     st.info(lang["enter_teacher_info"])

        for teacher_name, teacher_info in filtered_teachers.items():
            st.subheader(teacher_name)
            subject_key = "subject_en" if selected_language == "English" else "subject_zh"
            # Use .get for safety in case subject keys are missing
            subject = teacher_info.get(subject_key, "N/A")
            grade = teacher_info.get("grade", "N/A")

            # Build description safely
            description_parts = []
            if subject and subject != "N/A":
                 description_parts.append(f"**{subject}**")
            if grade and grade != "N/A":
                 description_parts.append(f"({lang['to_grade']} **{grade}**)")

            if description_parts:
                st.write(f"{lang['teaches']} {' '.join(description_parts)}")
            else:
                st.write(f"({lang['teaches']} N/A)") # Fallback if no subject/grade

            # Enrollment status and buttons
            current_enrollment_count = len(enrollments.get(teacher_name, []))
            cap = teacher_info.get("enrollment_cap") # Can be None or a number

            if cap is None or not isinstance(cap, int) or cap <= 0:
                cap_display = lang["unlimited"]
                is_full = False
            else:
                cap_display = str(cap)
                is_full = current_enrollment_count >= cap

            caption = lang["user_enrollment_caption"].format(count=current_enrollment_count, cap=cap_display)
            st.caption(caption)

            col1, col2 = st.columns(2)
            is_enrolled = user_name in enrollments.get(teacher_name, [])

            with col1:
                enroll_disabled = is_enrolled or is_full
                enroll_label = lang["enroll_button"]
                if is_full and not is_enrolled:
                    enroll_label = lang["enrollment_full"]

                enroll_clicked = st.button(
                    enroll_label,
                    key=f"enroll_button_{teacher_name}_{secure_id}", # Make key more unique
                    disabled=enroll_disabled,
                    use_container_width=True
                )

            with col2:
                cancel_clicked = st.button(
                    lang["cancel_button"],
                    key=f"cancel_button_{teacher_name}_{secure_id}", # Make key more unique
                    disabled=not is_enrolled,
                    use_container_width=True
                )

            # --- Button Actions ---
            if enroll_clicked: # No need to check !is_enrolled and !is_full due to disabled state
                if teacher_name not in enrollments:
                    enrollments[teacher_name] = []
                # Ensure student is not added twice (though button should be disabled)
                if user_name not in enrollments[teacher_name]:
                    enrollments[teacher_name].append(user_name)
                    save_data(ENROLLMENTS_DB_PATH, enrollments)
                    st.success(lang["enroll_success"].format(name=user_name, teacher=teacher_name))
                    st.rerun() # Rerun to update UI state
                else:
                     st.warning("Already enrolled.") # Should not happen if disabled correctly

            if cancel_clicked: # No need to check is_enrolled due to disabled state
                if teacher_name in enrollments and user_name in enrollments[teacher_name]:
                    enrollments[teacher_name].remove(user_name)
                    # If the list becomes empty, remove the teacher's key
                    if not enrollments[teacher_name]:
                        del enrollments[teacher_name]
                    save_data(ENROLLMENTS_DB_PATH, enrollments)
                    st.info(lang["enrollment_cancelled"])
                    st.rerun() # Rerun to update UI state
                else:
                    st.error(lang["not_enrolled"]) # Should not happen if disabled correctly

            # --- Enrollment List Expander ---
            with st.expander(f"{lang['enrolled_label']} ({current_enrollment_count})"):
                current_teacher_enrollments = enrollments.get(teacher_name, [])
                if current_teacher_enrollments:
                    # Display as numbered list
                    for i, student_name in enumerate(current_teacher_enrollments, 1):
                        display_name = f"{i}. {student_name}"
                        if student_name == user_name:
                            display_name += " **(You / 你)**" # Bilingual marker
                        st.markdown(display_name)
                else:
                    st.write(lang["no_enrollments"])
            st.markdown("---") # Separator between teachers
