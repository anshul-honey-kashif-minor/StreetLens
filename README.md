# StreetLens

StreetLens is an AI-powered image analysis tool that extracts structured information (Shop Name, Phone Numbers, Address, Category) from images of shop banners and storefronts. 

It compares the results of two advanced OCR and AI engines (EasyOCR and Gemini Vision) to provide the most accurate data, while allowing human verification before saving to a MySQL database.

## Features
- **Dual Engine Analysis:** Uses both EasyOCR and Gemini Vision to extract text and details.
- **Side-by-Side Comparison:** Compare the results of both engines directly in the UI and select the best one.
- **Human Verification:** Edit the extracted details on a split-screen view containing the original image.
- **Fuzzy Search:** Search the database of extracted shops with typo-tolerant fuzzy matching.
- **Modern UI:** Premium dark-mode, glassmorphic design that provides a stunning user experience.
- **Unified Startup:** Run the entire stack (FastAPI backend + Flask frontend) with a single command.

## Setup

0. **Kill port 8000 if in use:**
```bash
netstat -ano | Select-String ":8000.*LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique | ForEach-Object { taskkill /F /PID $_ }
```

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment variables:**
   Update your `.env` file with your MySQL credentials and Gemini API Key:
   ```ini
   GEMINI_API_KEY=your_api_key_here
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=mysql
   MYSQL_DATABASE=streetlens
   DATABASE_URL=mysql+pymysql://root:mysql@127.0.0.1:3306/streetlens
   ```

## Usage

Start the entire application using the single `run.py` script:

```bash
python run.py
```

This will automatically launch:
1. The FastAPI Backend on `http://127.0.0.1:8000`
2. The Flask Frontend on `http://127.0.0.1:5000`

Open your browser to `http://127.0.0.1:5000` to access the UI. Upload an image to see the dual-engine extraction in action!
