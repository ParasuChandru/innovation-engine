-- Drop tables if they exist to start fresh
DROP TABLE IF EXISTS ideas;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS spoc_mapping;
DROP TABLE IF EXISTS settings;

-- Users table to store user information
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('OWNER', 'SPOC', 'CGI_EXEC', 'LT_EXEC', 'ADMIN'))
);

-- Ideas table to store all idea submissions
CREATE TABLE ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    submitter_id INTEGER NOT NULL,
    spoc_id INTEGER,
    status TEXT NOT NULL,
    category TEXT NOT NULL,
    sub_category TEXT,
    problem_statement TEXT NOT NULL,
    proposed_solution TEXT NOT NULL,
    support_needed TEXT,
    users_impacted TEXT,
    business_impact TEXT,
    complexity TEXT,
    tools_used TEXT,
    est_cost_time TEXT,
    proj_savings REAL,
    hours_saved REAL,
    savings_measurement TEXT,
    target_completion_date TEXT,
    target_pi TEXT,
    jira_ticket_link TEXT,
    document_filename TEXT,
    document_original_filename TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submitter_id) REFERENCES users (id),
    FOREIGN KEY (spoc_id) REFERENCES users (id)
);

-- SPOC mapping table to link categories to SPOCs
CREATE TABLE spoc_mapping (
    category TEXT PRIMARY KEY,
    spoc_id INTEGER NOT NULL,
    FOREIGN KEY (spoc_id) REFERENCES users (id)
);

-- Settings table for application-wide configurations
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
