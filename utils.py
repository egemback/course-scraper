def apply_filters(df, semester_filter, final_filter, period_filter):
    filtered = df.copy()
    
    if semester_filter:
        filtered = df[df["Semester"].isin(semester_filter)]

    if final_filter == "Yes":
        filtered = filtered[filtered["Has Final"]]
    elif final_filter == "No":
        filtered = filtered[~filtered["Has Final"]]

    if period_filter:
        filtered = filtered[filtered["Periods"].apply(lambda x: any(p in x for p in period_filter))]

    return filtered
