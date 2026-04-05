import csv

def logText(text_lines, path) :
    LOG_FILES = "ocr_logs.csv"
    
    # file_exists = os.path.isfile(LOG_FILES)

    with open (LOG_FILES, "a", newline="", encoding="utf-8") as f :
        writer = csv.writer(f)

        combined_text = " | ".join(text_lines)

        writer.writerow([
        path,
        combined_text
        ])