def safe_split(text, start_marker, end_marker):
    try:
        return text.split(start_marker)[1].split(end_marker)[0].strip()
    except Exception:
        return ""