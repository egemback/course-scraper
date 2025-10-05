import time
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- Setup Selenium Driver ---
def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")   # headless Chrome
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

@st.cache_data(show_spinner=False)
def fetch_page(link: str) -> str:
    """Load a page fully with Selenium and return its HTML."""
    driver = init_driver()
    try:
        driver.get(link)
        time.sleep(2)  # wait for content to load
        html = driver.page_source
    finally:
        driver.quit()
    return html

@st.cache_data()
def scrape_courses(url: str) -> pd.DataFrame:
    driver = init_driver()
    driver.get(url)
    time.sleep(3)  # let the JS load course cards

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    courses = []
    base = "https://www.kth.se"

    for c in soup.select("div.course-card"):
        code = c.select_one("span.course-code").get_text(strip=True) if c.select_one("span.course-code") else "N/A"
        title = c.select_one("h3").get_text(strip=True) if c.select_one("h3") else "N/A"
        link = base + c.select_one("div.course-link > a")["href"] if c.select_one("div.course-link > a") else None

        semester = "Unknown"
        if "semesters=" in url:
            semester = url.split("semesters=")[1].split("&")[0]

        # Extract periods directly from card if available
        periods = []
        text = c.select_one("span.course-period").get_text(strip=True)
        for p in ["P1", "P2", "P3", "P4"]:
            if p in text:
                periods.append(p)

        # Now dive into course page for exam info
        has_final = False
        if link:
            try:
                html = fetch_page(link)
                d_soup = BeautifulSoup(html, "html.parser")
                text = d_soup.get_text(" ", strip=True)
                if "TEN" in text:
                    has_final = True
            except Exception as e:
                print(f"Error scraping {link}: {e}")

        courses.append({
            "Code": code,
            "Title": title,
            "Semester": semester,
            "Periods": ", ".join(periods) if periods else "Unknown",
            "Has Final": has_final,
            "Link": link
        })

    return pd.DataFrame(courses)
