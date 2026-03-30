# Job Application Tracker

A full-stack Flask + MySQL web app for tracking companies, jobs, applications, contacts, and skill-to-job matches.

## Features

- Dashboard with application summary metrics
- Full CRUD for `companies`, `jobs`, `applications`, and `contacts`
- Detail pages for every entity
- Job Match feature that ranks roles by match percentage
- MySQL schema with foreign keys and JSON columns

## Tech Stack

- Python 3.12
- Flask
- MySQL
- HTML/CSS

## Setup

1. Create a virtual environment:

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Configure your local database credentials in `.env`:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=job_application_tracker
```

4. Create the MySQL database and tables:

```powershell
python init_db.py
```

You can also run `schema.sql` manually in MySQL if you prefer.

5. Set environment variables as needed:

```powershell
$env:SECRET_KEY="change-me"
$env:DB_HOST="127.0.0.1"
$env:DB_PORT="3306"
$env:DB_USER="root"
$env:DB_PASSWORD="your-password"
$env:DB_NAME="job_application_tracker"
```

6. Run the app:

```powershell
python app.py
```

7. Open `http://127.0.0.1:5000`

## Notes

- Delete actions use MySQL foreign key cascades for related child records.
- The Job Match feature compares entered skills against each job's `required_skills_json`.
- Add at least one company before creating jobs, and at least one job before creating applications.
