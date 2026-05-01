## To Run

Start the FastAPI backend:

```cmd
uvicorn app:app --reload
```

The FastAPI backend exposes:

```text
POST /image-analyzer
```

The backend now runs two OCR engines in parallel for each upload:

- `Gemini Vision`
- `EasyOCR`

The response includes a comparison payload plus a default selected result. The Flask frontend shows both outputs side by side so the user can apply either one into the editable review form.

Start the Flask frontend in another terminal:

```cmd
python frontend/app.py
```

Open:

```text
http://127.0.0.1:5000
```

MySQL defaults:

```text
host: localhost
user: root
password: mysql
database: streetlens
```

Optional environment overrides:

```text
STREETLENS_API_URL=http://127.0.0.1:8000/image-analyzer
STREETLENS_DATABASE_URL=mysql+pymysql://root:mysql@localhost/streetlens?charset=utf8mb4
STREETLENS_FLASK_PORT=5000
EASYOCR_LANGUAGES=en,hi
EASYOCR_GPU=0
```

Notes:

- EasyOCR may download model weights on first run.
- For mixed English and Hindi storefronts, the default language list is `en,hi`.
- `EASYOCR_GPU=1` should only be enabled when CUDA-ready PyTorch is installed.
