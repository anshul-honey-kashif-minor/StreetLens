## To Run
```cmd
python run_app.py
```
Start the FastAPI backend:

```cmd
uvicorn app:app --reload
```

The FastAPI backend exposes:

```text
POST /image-analyzer
```

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
```
