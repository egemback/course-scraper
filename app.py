import os
import streamlit as st
from scraper import scrape_courses
from utils import apply_filters
import pandas as pd
import datetime

st.set_page_config(page_title="KTH Course Catalog Filter", layout="wide")
st.title("KTH Course Catalog Filter")

if "df" not in st.session_state:
    # Get current year and month
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month

    # Determine next semester and year
    if current_month >= 9:
        next_semester = "VT"
    else:
        next_semester = "HT"

    # Semester dropdown (do not show current semester)
    semester_options = []
    if next_semester == "VT":
        semester_options = [f"VT{current_year + 1}", f"HT{current_year + 1}"]
    else:
        semester_options = [f"HT{current_year}", f"VT{current_year + 1}"]

    st.markdown("### Select Course Catalog Parameters")

    # Semester selection (only next semester)
    semester = st.selectbox("Semester", semester_options, index=0, key="semester")
    st.session_state.semester_filter = semester

    # Educational level dropdown
    edu_level_map = {"Both": "0", "Bachelor": "1", "Master": "2"}
    edu_level = st.selectbox("Educational Level", ["Both", "Bachelor", "Master"], index=2)
    edu_level_code = edu_level_map[edu_level]
    if edu_level_code == "0":
        edu_level_code = ["1", "2"]
    else:
        edu_level_code = [edu_level_code]
    st.session_state.edu_level_code = edu_level_code

    # Subject code selection: allow multiple predefined codes and extra custom codes
    subject_options = ["ME", "SF", "SK", "SG", "JH"]
    select_all_subjects = st.checkbox("Select All Prescraped Subjects", value=False)
    selected_subjects = st.multiselect("Subject Codes (choose one or more)", subject_options, disabled=select_all_subjects)

    st.markdown("Or add custom subject codes (comma-separated), e.g. ME,SF")
    custom_subjects_raw = st.text_input("Custom subject codes:", "", disabled=select_all_subjects)
    
    all_subjects = [[], []] if len(edu_level_code) == 2 else [[]]
    if select_all_subjects:
        for file in os.listdir("data"):
            if file.endswith(".json"):
                if semester in file and file.split("_")[2] in edu_level_code:
                    subject_code = file.split("_")[3].replace(".json", "")
                    all_subjects[0].append(subject_code) if len(edu_level_code) == 1 else all_subjects[int(file.split("_")[2]) - 1].append(subject_code)
    else:
        # Normalize and merge subject codes into a comma-separated department parameter
        custom_subjects = [s.strip().upper() for s in custom_subjects_raw.split(",") if s.strip()] if custom_subjects_raw else []
        tmp_all_subjects = selected_subjects + custom_subjects
        all_subjects[0] = list(set(tmp_all_subjects))  # Remove duplicates
    

    # Compose URL (include department param only if provided)
    base_url = "https://www.kth.se/student/kurser/sokkurs/resultat"
    urls = []
    for i, edu_level in enumerate(edu_level_code):
        custom_base_url = f"{base_url}?semesters={semester}&eduLevel={edu_level}"
        for subject in all_subjects[i]:
            urls.append(f"{custom_base_url}&department={subject}")

    if st.button("Scrape Courses"):
        if not all_subjects:
            st.warning("Please select at least one subject code or enter a custom subject code.")
            st.stop()
            
        with st.spinner("Scraping courses (cached where possible)..."):
            try:
                df = pd.DataFrame()
                for url in urls:
                    df = pd.concat([df, scrape_courses(url)], ignore_index=True)
                    
                if df.empty:
                    st.session_state.error = True
                else:
                    st.session_state.df = df
                    st.session_state.all_subjects = all_subjects
                    
                st.rerun()
            except Exception as e:
                print(f"Error during scraping: {e}")
                st.session_state.error = True
    
    if "error" in st.session_state and st.session_state.error:
        st.warning("No courses found")
        del st.session_state.error
else:
    df = st.session_state.df
    with st.sidebar:
        st.header("Filters")

        periods = ["P1", "P2", "P3", "P4"]
        period_filter = st.multiselect("Period", periods)
        exclusive_period = st.checkbox("Match periods exactly", value=False)

        final_filter = st.selectbox("Has Final Exam?", ["All", "Yes", "No"])
        
        if len(st.session_state.edu_level_code) == 2:
            edu_level_filter = st.selectbox("Educational Level", ["Both", "Bachelor", "Master"])
        else:
            edu_level_filter = None

        # Subject filter
        subject_filter = st.multiselect("Subject", st.session_state.all_subjects)

        # Add ECTS credits slider
        ects_min = float(df["ECTS"].min())
        ects_max = float(df["ECTS"].max())
        ects_range = st.slider(
            "ECTS Credits",
            min_value=ects_min,
            max_value=ects_max,
            value=(ects_min, ects_max),
            step=1.5  # Common step for ECTS credits
        )
        
        subject_codes = sorted(set(code.split(" ")[0] for code in df["Code"]))
        
        if st.button("New Search"):
            del st.session_state.df
            st.rerun()

    # Apply filters
    filtered = apply_filters(df, [st.session_state.semester_filter], final_filter, period_filter, exclusive_period, ects_range, edu_level_filter, subject_filter)

    st.info(f"Showing {len(filtered)} courses (from {len(df)} total scraped).")

    # Show full table
    st.dataframe(filtered, use_container_width=True, hide_index=True, column_order=["Code", "Title", "Periods", "Has Final", "ECTS"])

    # Allow user to select a course
    selected_course = st.selectbox(
        "Select a course to view its page",
        options=filtered["Code"] if not filtered.empty else [],
        index=0 if not filtered.empty else None
    )

    # Assume course page URL follows this pattern:
    course_url = f"https://www.kth.se/student/kurser/kurs/{selected_course}"
    st.markdown(
        f'<a href="{course_url}" target="_blank"><button style="background-color:#4CAF50;color:white;padding:8px 16px;border:none;border-radius:4px;cursor:pointer;">Open Course Page</button></a>',
        unsafe_allow_html=True
    )

    # CSV download
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download as CSV", data=csv, file_name="courses.csv", mime="text/csv")
