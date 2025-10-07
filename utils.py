import os
import json
from datetime import datetime, timedelta

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_EXPIRY_DAYS = 90  # 3 months

def apply_filters(df, semester_filter, final_filter, period_filter, exclusive_period=False, ects_range=None, edu_level_filter=None, subject_filter=None):
    filtered = df.copy()
    
    if semester_filter:
        filtered = filtered[filtered["Semester"].isin(semester_filter)]

    if final_filter == "Yes":
        filtered = filtered[filtered["Has Final"]]
    elif final_filter == "No":
        filtered = filtered[~filtered["Has Final"]]

    if period_filter:
        filtered = filtered[filtered["Periods"].apply(lambda x: any(p in x for p in period_filter) and (len(x.split()) == len(period_filter) or not exclusive_period))]
        
    if ects_range:
        filtered = filtered[
            (filtered["ECTS"] >= ects_range[0]) & 
            (filtered["ECTS"] <= ects_range[1])
        ]
        
    if edu_level_filter and edu_level_filter != "Both":
        level_map = {"Bachelor": 1, "Master": 2}
        filtered = filtered[filtered["Code"].apply(lambda x: int(x[2]) == level_map[edu_level_filter])]
        
    if subject_filter:
        filtered = filtered[filtered["Subject"].isin(subject_filter)]

    return filtered

def get_cache_path(semester, edu_level, subject):
    """Get the path to the cache file for a specific semester."""
    return os.path.join(CACHE_DIR, f"courses_{semester}_{edu_level}_{subject}.json")

def load_cached_courses(semester, edu_level, subject):
    """Load courses from cache if available and not expired."""
    cache_path = get_cache_path(semester, edu_level, subject)
    
    if not os.path.exists(cache_path):
        return None
        
    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
            
        # Check if cache is expired (older than 3 months)
        cache_timestamp = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - cache_timestamp > timedelta(days=CACHE_EXPIRY_DAYS):
            return None
            
        return cache_data['courses']
    except (json.JSONDecodeError, KeyError, ValueError):
        return None

def save_courses_to_cache(semester, edu_level, subject, courses):
    """Save courses to cache with current timestamp."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        
    cache_data = {
        'timestamp': datetime.now().isoformat(),
        'courses': courses
    }
    
    cache_path = get_cache_path(semester, edu_level, subject)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(cache_data, f, indent=2)
