# Student Placement System

A local Flask and SQLite web app for student placement opportunities. Flask serves the active frontend from `Front end/` and exposes the JSON API used for authentication, profiles, eligibility, applications, notifications, saved jobs, and placement-cell management.

## Run on Windows

Open this repository root in VS Code. In a terminal at the project root, run:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r PYTHON_FOLDER\requirements.txt
```

Then press **Ctrl+Shift+B** and select **Start Student Placement Server**, or run:

```powershell
.\start.ps1
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/). Stop the background server with `powershell -NoProfile -ExecutionPolicy Bypass -File .\stop.ps1`. Alternatively, select **Run Student Placement System** in VS Code's Run and Debug panel and open the same URL.

## Demo accounts

- Student: `student1@placement.demo` / `student123`
- Admin: `admin@pathway.demo` / `admin123`

Students can also create an account through the registration page. These demo credentials are for local development only.

## Project layout

- `PYTHON_FOLDER/main.py`: Flask app and API routes.
- `PYTHON_FOLDER/database.py`: SQLite schema, demo seed data, and database access.
- `PYTHON_FOLDER/eligibility.py`, `placement.py`, `student.py`, `company.py`: placement rules and source records.
- `Front end/`: active HTML, CSS, and JavaScript client served by Flask.
- `FRONTEND_FOLDER/`: older duplicate frontend snapshot; Flask does not serve this folder.
- `placement.db`: created automatically on first run; ignored by Git.

The frontend talks to `/api/...` on the same origin, so do not open HTML files directly or use Live Server. Use the Flask URL above. Resume values are currently filenames only; file upload and production deployment configuration are not implemented.
