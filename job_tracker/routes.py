from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .db import get_cursor
from .utils import expand_skills, json_dumps, json_loads, normalize_skills, parse_csv, parse_lines, parse_skills

main = Blueprint("main", __name__)

APPLICATION_STATUSES = [
    "Saved",
    "Applied",
    "Interviewing",
    "Offer",
    "Rejected",
]


def fetch_all(query: str, params: tuple = ()):
    with get_cursor() as (_, cursor):
        cursor.execute(query, params)
        return cursor.fetchall()


def fetch_one(query: str, params: tuple = ()):
    with get_cursor() as (_, cursor):
        cursor.execute(query, params)
        return cursor.fetchone()


def execute(query: str, params: tuple = ()):
    with get_cursor() as (_, cursor):
        cursor.execute(query, params)
        return cursor.lastrowid


def require_text(value: str, label: str, errors: list[str]):
    cleaned = value.strip()
    if not cleaned:
        errors.append(f"{label} is required.")
    return cleaned


def get_required_record(query: str, params: tuple = ()):
    record = fetch_one(query, params)
    if record is None:
        abort(404)
    return record


def get_companies():
    return fetch_all(
        """
        SELECT company_id, name, industry, location, website, company_size
        FROM companies
        ORDER BY name
        """
    )


def get_jobs():
    return fetch_all(
        """
        SELECT jobs.job_id, jobs.title, jobs.location, jobs.salary_range, jobs.posted_date,
               jobs.application_deadline, companies.name AS company_name
        FROM jobs
        JOIN companies ON companies.company_id = jobs.company_id
        ORDER BY jobs.posted_date DESC, jobs.title
        """
    )


def get_applications():
    return fetch_all(
        """
        SELECT applications.application_id, applications.status, applications.applied_date,
               applications.source, jobs.title AS job_title, companies.name AS company_name
        FROM applications
        JOIN jobs ON jobs.job_id = applications.job_id
        JOIN companies ON companies.company_id = jobs.company_id
        ORDER BY applications.applied_date DESC, applications.application_id DESC
        """
    )


def get_contacts():
    return fetch_all(
        """
        SELECT contacts.contact_id, contacts.full_name, contacts.email, contacts.role_title,
               contacts.relationship_type, companies.name AS company_name
        FROM contacts
        JOIN companies ON companies.company_id = contacts.company_id
        ORDER BY contacts.full_name
        """
    )


@main.route("/")
def dashboard():
    stats = {
        "companies": fetch_one("SELECT COUNT(*) AS total FROM companies")["total"],
        "jobs": fetch_one("SELECT COUNT(*) AS total FROM jobs")["total"],
        "applications": fetch_one("SELECT COUNT(*) AS total FROM applications")["total"],
        "contacts": fetch_one("SELECT COUNT(*) AS total FROM contacts")["total"],
    }
    by_status = fetch_all(
        """
        SELECT status, COUNT(*) AS total
        FROM applications
        GROUP BY status
        ORDER BY total DESC, status
        """
    )
    recent_applications = fetch_all(
        """
        SELECT applications.application_id, applications.status, applications.applied_date,
               jobs.title AS job_title, companies.name AS company_name
        FROM applications
        JOIN jobs ON jobs.job_id = applications.job_id
        JOIN companies ON companies.company_id = jobs.company_id
        ORDER BY applications.applied_date DESC, applications.application_id DESC
        LIMIT 5
        """
    )
    return render_template(
        "dashboard.html",
        stats=stats,
        by_status=by_status,
        recent_applications=recent_applications,
    )


@main.route("/companies")
def company_list():
    return render_template("companies/list.html", companies=get_companies())


@main.route("/companies/<int:company_id>")
def company_detail(company_id: int):
    company = get_required_record("SELECT * FROM companies WHERE company_id = %s", (company_id,))
    jobs = fetch_all(
        """
        SELECT job_id, title, location, employment_type
        FROM jobs
        WHERE company_id = %s
        ORDER BY posted_date DESC, title
        """,
        (company_id,),
    )
    contacts = fetch_all(
        """
        SELECT contact_id, full_name, email, relationship_type
        FROM contacts
        WHERE company_id = %s
        ORDER BY full_name
        """,
        (company_id,),
    )
    return render_template("companies/detail.html", company=company, jobs=jobs, contacts=contacts)


@main.route("/companies/new", methods=["GET", "POST"])
def company_create():
    company = {
        "name": "",
        "industry": "",
        "location": "",
        "website": "",
        "company_size": "",
        "notes": "",
        "tags": "",
    }
    if request.method == "POST":
        errors = []
        company = {
            "name": require_text(request.form.get("name", ""), "Company name", errors),
            "industry": request.form.get("industry", "").strip(),
            "location": request.form.get("location", "").strip(),
            "website": request.form.get("website", "").strip(),
            "company_size": request.form.get("company_size", "").strip(),
            "notes": request.form.get("notes", "").strip(),
            "tags": request.form.get("tags", "").strip(),
        }
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            execute(
                """
                INSERT INTO companies (name, industry, location, website, company_size, notes, tags_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    company["name"],
                    company["industry"],
                    company["location"],
                    company["website"],
                    company["company_size"],
                    company["notes"],
                    json_dumps(parse_csv(company["tags"])),
                ),
            )
            flash("Company created successfully.", "success")
            return redirect(url_for("main.company_list"))
    return render_template("companies/form.html", company=company, editing=False)


@main.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id: int):
    row = get_required_record("SELECT * FROM companies WHERE company_id = %s", (company_id,))
    company = {
        "name": row["name"],
        "industry": row["industry"] or "",
        "location": row["location"] or "",
        "website": row["website"] or "",
        "company_size": row["company_size"] or "",
        "notes": row["notes"] or "",
        "tags": ", ".join(json_loads(row["tags_json"])),
    }
    if request.method == "POST":
        errors = []
        company = {
            "name": require_text(request.form.get("name", ""), "Company name", errors),
            "industry": request.form.get("industry", "").strip(),
            "location": request.form.get("location", "").strip(),
            "website": request.form.get("website", "").strip(),
            "company_size": request.form.get("company_size", "").strip(),
            "notes": request.form.get("notes", "").strip(),
            "tags": request.form.get("tags", "").strip(),
        }
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            execute(
                """
                UPDATE companies
                SET name = %s, industry = %s, location = %s, website = %s,
                    company_size = %s, notes = %s, tags_json = %s
                WHERE company_id = %s
                """,
                (
                    company["name"],
                    company["industry"],
                    company["location"],
                    company["website"],
                    company["company_size"],
                    company["notes"],
                    json_dumps(parse_csv(company["tags"])),
                    company_id,
                ),
            )
            flash("Company updated successfully.", "success")
            return redirect(url_for("main.company_detail", company_id=company_id))
    return render_template("companies/form.html", company=company, editing=True, company_id=company_id)


@main.post("/companies/<int:company_id>/delete")
def company_delete(company_id: int):
    execute("DELETE FROM companies WHERE company_id = %s", (company_id,))
    flash("Company deleted.", "success")
    return redirect(url_for("main.company_list"))


@main.route("/jobs")
def job_list():
    return render_template("jobs/list.html", jobs=get_jobs())


@main.route("/jobs/<int:job_id>")
def job_detail(job_id: int):
    job = get_required_record(
        """
        SELECT jobs.*, companies.name AS company_name
        FROM jobs
        JOIN companies ON companies.company_id = jobs.company_id
        WHERE jobs.job_id = %s
        """,
        (job_id,),
    )
    job["required_skills"] = json_loads(job["required_skills_json"])
    job["preferred_skills"] = json_loads(job["preferred_skills_json"])
    applications = fetch_all(
        """
        SELECT application_id, status, applied_date
        FROM applications
        WHERE job_id = %s
        ORDER BY applied_date DESC
        """,
        (job_id,),
    )
    return render_template("jobs/detail.html", job=job, applications=applications)


@main.route("/jobs/new", methods=["GET", "POST"])
def job_create():
    companies = get_companies()
    job = {
        "company_id": "",
        "title": "",
        "location": "",
        "salary_range": "",
        "employment_type": "",
        "posted_date": date.today().isoformat(),
        "application_deadline": "",
        "description": "",
        "required_skills": "",
        "preferred_skills": "",
    }
    if request.method == "POST":
        errors = []
        job = {
            "company_id": require_text(request.form.get("company_id", ""), "Company", errors),
            "title": require_text(request.form.get("title", ""), "Job title", errors),
            "location": request.form.get("location", "").strip(),
            "salary_range": request.form.get("salary_range", "").strip(),
            "employment_type": request.form.get("employment_type", "").strip(),
            "posted_date": require_text(request.form.get("posted_date", ""), "Posted date", errors),
            "application_deadline": request.form.get("application_deadline", "").strip() or None,
            "description": request.form.get("description", "").strip(),
            "required_skills": request.form.get("required_skills", "").strip(),
            "preferred_skills": request.form.get("preferred_skills", "").strip(),
        }
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            execute(
                """
                INSERT INTO jobs (
                    company_id, title, location, salary_range, employment_type,
                    posted_date, application_deadline, description,
                    required_skills_json, preferred_skills_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    job["company_id"],
                    job["title"],
                    job["location"],
                    job["salary_range"],
                    job["employment_type"],
                    job["posted_date"],
                    job["application_deadline"],
                    job["description"],
                    json_dumps(parse_skills(job["required_skills"])),
                    json_dumps(parse_skills(job["preferred_skills"])),
                ),
            )
            flash("Job created successfully.", "success")
            return redirect(url_for("main.job_list"))
    return render_template("jobs/form.html", job=job, companies=companies, editing=False)


@main.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id: int):
    companies = get_companies()
    row = get_required_record("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    job = {
        "company_id": str(row["company_id"]),
        "title": row["title"],
        "location": row["location"] or "",
        "salary_range": row["salary_range"] or "",
        "employment_type": row["employment_type"] or "",
        "posted_date": row["posted_date"].isoformat() if row["posted_date"] else "",
        "application_deadline": row["application_deadline"].isoformat() if row["application_deadline"] else "",
        "description": row["description"] or "",
        "required_skills": "\n".join(expand_skills(json_loads(row["required_skills_json"]))),
        "preferred_skills": "\n".join(expand_skills(json_loads(row["preferred_skills_json"]))),
    }
    if request.method == "POST":
        errors = []
        job = {
            "company_id": require_text(request.form.get("company_id", ""), "Company", errors),
            "title": require_text(request.form.get("title", ""), "Job title", errors),
            "location": request.form.get("location", "").strip(),
            "salary_range": request.form.get("salary_range", "").strip(),
            "employment_type": request.form.get("employment_type", "").strip(),
            "posted_date": require_text(request.form.get("posted_date", ""), "Posted date", errors),
            "application_deadline": request.form.get("application_deadline", "").strip() or None,
            "description": request.form.get("description", "").strip(),
            "required_skills": request.form.get("required_skills", "").strip(),
            "preferred_skills": request.form.get("preferred_skills", "").strip(),
        }
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            execute(
                """
                UPDATE jobs
                SET company_id = %s, title = %s, location = %s, salary_range = %s,
                    employment_type = %s, posted_date = %s, application_deadline = %s,
                    description = %s, required_skills_json = %s, preferred_skills_json = %s
                WHERE job_id = %s
                """,
                (
                    job["company_id"],
                    job["title"],
                    job["location"],
                    job["salary_range"],
                    job["employment_type"],
                    job["posted_date"],
                    job["application_deadline"],
                    job["description"],
                    json_dumps(parse_skills(job["required_skills"])),
                    json_dumps(parse_skills(job["preferred_skills"])),
                    job_id,
                ),
            )
            flash("Job updated successfully.", "success")
            return redirect(url_for("main.job_detail", job_id=job_id))
    return render_template("jobs/form.html", job=job, companies=companies, editing=True, job_id=job_id)


@main.post("/jobs/<int:job_id>/delete")
def job_delete(job_id: int):
    execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
    flash("Job deleted.", "success")
    return redirect(url_for("main.job_list"))


@main.route("/applications")
def application_list():
    return render_template("applications/list.html", applications=get_applications())


@main.route("/applications/<int:application_id>")
def application_detail(application_id: int):
    application = get_required_record(
        """
        SELECT applications.*, jobs.title AS job_title, companies.name AS company_name
        FROM applications
        JOIN jobs ON jobs.job_id = applications.job_id
        JOIN companies ON companies.company_id = jobs.company_id
        WHERE applications.application_id = %s
        """,
        (application_id,),
    )
    application["follow_up_tasks"] = json_loads(application["follow_up_tasks_json"])
    return render_template("applications/detail.html", application=application)


@main.route("/applications/new", methods=["GET", "POST"])
def application_create():
    jobs = get_jobs()
    application = {
        "job_id": "",
        "status": "Applied",
        "applied_date": date.today().isoformat(),
        "source": "",
        "resume_version": "",
        "cover_letter_used": "no",
        "follow_up_tasks": "",
        "notes": "",
    }
    if request.method == "POST":
        errors = []
        application = {
            "job_id": require_text(request.form.get("job_id", ""), "Job", errors),
            "status": require_text(request.form.get("status", ""), "Status", errors),
            "applied_date": require_text(request.form.get("applied_date", ""), "Applied date", errors),
            "source": request.form.get("source", "").strip(),
            "resume_version": request.form.get("resume_version", "").strip(),
            "cover_letter_used": request.form.get("cover_letter_used", "no").strip(),
            "follow_up_tasks": request.form.get("follow_up_tasks", "").strip(),
            "notes": request.form.get("notes", "").strip(),
        }
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            execute(
                """
                INSERT INTO applications (
                    job_id, status, applied_date, source, resume_version,
                    cover_letter_used, follow_up_tasks_json, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    application["job_id"],
                    application["status"],
                    application["applied_date"],
                    application["source"],
                    application["resume_version"],
                    1 if application["cover_letter_used"] == "yes" else 0,
                    json_dumps(parse_lines(application["follow_up_tasks"])),
                    application["notes"],
                ),
            )
            flash("Application created successfully.", "success")
            return redirect(url_for("main.application_list"))
    return render_template(
        "applications/form.html",
        application=application,
        jobs=jobs,
        statuses=APPLICATION_STATUSES,
        editing=False,
    )


@main.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_edit(application_id: int):
    jobs = get_jobs()
    row = get_required_record("SELECT * FROM applications WHERE application_id = %s", (application_id,))
    application = {
        "job_id": str(row["job_id"]),
        "status": row["status"],
        "applied_date": row["applied_date"].isoformat() if row["applied_date"] else "",
        "source": row["source"] or "",
        "resume_version": row["resume_version"] or "",
        "cover_letter_used": "yes" if row["cover_letter_used"] else "no",
        "follow_up_tasks": "\n".join(json_loads(row["follow_up_tasks_json"])),
        "notes": row["notes"] or "",
    }
    if request.method == "POST":
        errors = []
        application = {
            "job_id": require_text(request.form.get("job_id", ""), "Job", errors),
            "status": require_text(request.form.get("status", ""), "Status", errors),
            "applied_date": require_text(request.form.get("applied_date", ""), "Applied date", errors),
            "source": request.form.get("source", "").strip(),
            "resume_version": request.form.get("resume_version", "").strip(),
            "cover_letter_used": request.form.get("cover_letter_used", "no").strip(),
            "follow_up_tasks": request.form.get("follow_up_tasks", "").strip(),
            "notes": request.form.get("notes", "").strip(),
        }
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            execute(
                """
                UPDATE applications
                SET job_id = %s, status = %s, applied_date = %s, source = %s,
                    resume_version = %s, cover_letter_used = %s,
                    follow_up_tasks_json = %s, notes = %s
                WHERE application_id = %s
                """,
                (
                    application["job_id"],
                    application["status"],
                    application["applied_date"],
                    application["source"],
                    application["resume_version"],
                    1 if application["cover_letter_used"] == "yes" else 0,
                    json_dumps(parse_lines(application["follow_up_tasks"])),
                    application["notes"],
                    application_id,
                ),
            )
            flash("Application updated successfully.", "success")
            return redirect(url_for("main.application_detail", application_id=application_id))
    return render_template(
        "applications/form.html",
        application=application,
        jobs=jobs,
        statuses=APPLICATION_STATUSES,
        editing=True,
        application_id=application_id,
    )


@main.post("/applications/<int:application_id>/delete")
def application_delete(application_id: int):
    execute("DELETE FROM applications WHERE application_id = %s", (application_id,))
    flash("Application deleted.", "success")
    return redirect(url_for("main.application_list"))


@main.route("/contacts")
def contact_list():
    return render_template("contacts/list.html", contacts=get_contacts())


@main.route("/contacts/<int:contact_id>")
def contact_detail(contact_id: int):
    contact = get_required_record(
        """
        SELECT contacts.*, companies.name AS company_name
        FROM contacts
        JOIN companies ON companies.company_id = contacts.company_id
        WHERE contacts.contact_id = %s
        """,
        (contact_id,),
    )
    contact["topics_discussed"] = json_loads(contact["topics_discussed_json"])
    return render_template("contacts/detail.html", contact=contact)


@main.route("/contacts/new", methods=["GET", "POST"])
def contact_create():
    companies = get_companies()
    contact = {
        "company_id": "",
        "full_name": "",
        "email": "",
        "phone": "",
        "role_title": "",
        "relationship_type": "",
        "linkedin_url": "",
        "topics_discussed": "",
        "notes": "",
    }
    if request.method == "POST":
        errors = []
        contact = {
            "company_id": require_text(request.form.get("company_id", ""), "Company", errors),
            "full_name": require_text(request.form.get("full_name", ""), "Full name", errors),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "role_title": request.form.get("role_title", "").strip(),
            "relationship_type": request.form.get("relationship_type", "").strip(),
            "linkedin_url": request.form.get("linkedin_url", "").strip(),
            "topics_discussed": request.form.get("topics_discussed", "").strip(),
            "notes": request.form.get("notes", "").strip(),
        }
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            execute(
                """
                INSERT INTO contacts (
                    company_id, full_name, email, phone, role_title,
                    relationship_type, linkedin_url, topics_discussed_json, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    contact["company_id"],
                    contact["full_name"],
                    contact["email"],
                    contact["phone"],
                    contact["role_title"],
                    contact["relationship_type"],
                    contact["linkedin_url"],
                    json_dumps(parse_lines(contact["topics_discussed"])),
                    contact["notes"],
                ),
            )
            flash("Contact created successfully.", "success")
            return redirect(url_for("main.contact_list"))
    return render_template("contacts/form.html", contact=contact, companies=companies, editing=False)


@main.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id: int):
    companies = get_companies()
    row = get_required_record("SELECT * FROM contacts WHERE contact_id = %s", (contact_id,))
    contact = {
        "company_id": str(row["company_id"]),
        "full_name": row["full_name"],
        "email": row["email"] or "",
        "phone": row["phone"] or "",
        "role_title": row["role_title"] or "",
        "relationship_type": row["relationship_type"] or "",
        "linkedin_url": row["linkedin_url"] or "",
        "topics_discussed": "\n".join(json_loads(row["topics_discussed_json"])),
        "notes": row["notes"] or "",
    }
    if request.method == "POST":
        errors = []
        contact = {
            "company_id": require_text(request.form.get("company_id", ""), "Company", errors),
            "full_name": require_text(request.form.get("full_name", ""), "Full name", errors),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "role_title": request.form.get("role_title", "").strip(),
            "relationship_type": request.form.get("relationship_type", "").strip(),
            "linkedin_url": request.form.get("linkedin_url", "").strip(),
            "topics_discussed": request.form.get("topics_discussed", "").strip(),
            "notes": request.form.get("notes", "").strip(),
        }
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            execute(
                """
                UPDATE contacts
                SET company_id = %s, full_name = %s, email = %s, phone = %s,
                    role_title = %s, relationship_type = %s, linkedin_url = %s,
                    topics_discussed_json = %s, notes = %s
                WHERE contact_id = %s
                """,
                (
                    contact["company_id"],
                    contact["full_name"],
                    contact["email"],
                    contact["phone"],
                    contact["role_title"],
                    contact["relationship_type"],
                    contact["linkedin_url"],
                    json_dumps(parse_lines(contact["topics_discussed"])),
                    contact["notes"],
                    contact_id,
                ),
            )
            flash("Contact updated successfully.", "success")
            return redirect(url_for("main.contact_detail", contact_id=contact_id))
    return render_template("contacts/form.html", contact=contact, companies=companies, editing=True, contact_id=contact_id)


@main.post("/contacts/<int:contact_id>/delete")
def contact_delete(contact_id: int):
    execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))
    flash("Contact deleted.", "success")
    return redirect(url_for("main.contact_list"))


@main.route("/job-match", methods=["GET", "POST"])
def job_match():
    results = []
    entered_skills = ""
    if request.method == "POST":
        entered_skills = request.form.get("skills", "").strip()
        normalized_input = normalize_skills(parse_csv(entered_skills))
        jobs = fetch_all(
            """
            SELECT jobs.job_id, jobs.title, jobs.location, jobs.required_skills_json,
                   companies.name AS company_name
            FROM jobs
            JOIN companies ON companies.company_id = jobs.company_id
            ORDER BY jobs.posted_date DESC, jobs.title
            """
        )
        for job in jobs:
            required = normalize_skills(json_loads(job["required_skills_json"]))
            matched = sorted(set(required) & set(normalized_input))
            score = round((len(matched) / len(required)) * 100) if required else 0
            missing = sorted(set(required) - set(normalized_input))
            results.append(
                {
                    "job_id": job["job_id"],
                    "title": job["title"],
                    "company_name": job["company_name"],
                    "location": job["location"],
                    "score": score,
                    "matched": matched,
                    "missing": missing,
                }
            )
        results.sort(key=lambda item: (-item["score"], item["title"].lower()))
    return render_template("job_match.html", results=results, entered_skills=entered_skills)
