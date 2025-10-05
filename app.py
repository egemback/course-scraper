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

    # Educational level dropdown
    edu_level_map = {"Bachelor": "1", "Master": "2"}
    edu_level = st.selectbox("Educational Level", ["Bachelor", "Master"], index=1)
    edu_level_code = edu_level_map[edu_level]

    # Subject code selection: allow multiple predefined codes and extra custom codes
    subject_options = ["ME", "SF", "DA"]
    selected_subjects = st.multiselect("Subject Codes (choose one or more)", subject_options, default=["ME"])

    st.markdown("Or add custom subject codes (comma-separated), e.g. EL,EE")
    custom_subjects_raw = st.text_input("Custom subject codes:", "")

    # Normalize and merge subject codes into a comma-separated department parameter
    custom_subjects = [s.strip().upper() for s in custom_subjects_raw.split(",") if s.strip()] if custom_subjects_raw else []
    all_subjects = selected_subjects + custom_subjects
    all_subjects = list(set(all_subjects))  # Remove duplicates

    # Compose URL (include department param only if provided)
    base_url = "https://www.kth.se/student/kurser/sokkurs/resultat"
    custom_base_url = f"{base_url}?semesters={semester}&eduLevel={edu_level_code}"
    urls = []
    for subject in all_subjects:
        urls.append(f"{custom_base_url}&department={subject}")

    if st.button("Scrape Courses"):
        with st.spinner("Scraping courses (cached where possible)..."):
            try:
                df = pd.DataFrame()
                for url in urls:
                    df = pd.concat([df, scrape_courses(url)], ignore_index=True)
                    
                if df.empty:
                    st.session_state.error = True
                    st.rerun()
                    
                st.session_state.df = df
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

        semesters = df["Semester"].unique().tolist()
        semester_filter = st.multiselect("Semester", semesters, default=semesters)

        periods = ["P1", "P2", "P3", "P4"]
        period_filter = st.multiselect("Period", periods)

        final_filter = st.selectbox("Has Final Exam?", ["All", "Yes", "No"])

        subject_codes = sorted(set(code.split(" ")[0] for code in df["Code"]))
        
        if st.button("New Search"):
            del st.session_state.df
            st.rerun()

    # Apply filters
    filtered = apply_filters(df, semester_filter, final_filter, period_filter)

    st.success(f"Showing {len(filtered)} courses (from {len(df)} total scraped).")

    # Show full table
    st.dataframe(filtered, use_container_width=True)

    # Preview raw data for debugging
    with st.expander("Raw scraped data preview"):
        st.write(df.head())

    # CSV download
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download as CSV", data=csv, file_name="courses.csv", mime="text/csv")
