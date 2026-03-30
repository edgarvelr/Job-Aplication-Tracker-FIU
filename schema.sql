CREATE DATABASE IF NOT EXISTS job_application_tracker;
USE job_application_tracker;

DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS companies;

CREATE TABLE companies (
    company_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    industry VARCHAR(100),
    location VARCHAR(150),
    website VARCHAR(255),
    company_size VARCHAR(50),
    notes TEXT,
    tags_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    location VARCHAR(150),
    salary_range VARCHAR(100),
    employment_type VARCHAR(50),
    posted_date DATE NOT NULL,
    application_deadline DATE,
    description TEXT,
    required_skills_json JSON,
    preferred_skills_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE
);

CREATE TABLE applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    applied_date DATE NOT NULL,
    source VARCHAR(100),
    resume_version VARCHAR(100),
    cover_letter_used BOOLEAN DEFAULT FALSE,
    follow_up_tasks_json JSON,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_applications_job
        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        ON DELETE CASCADE
);

CREATE TABLE contacts (
    contact_id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(50),
    role_title VARCHAR(100),
    relationship_type VARCHAR(100),
    linkedin_url VARCHAR(255),
    topics_discussed_json JSON,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contacts_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE
);
