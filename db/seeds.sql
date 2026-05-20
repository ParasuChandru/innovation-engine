-- Clear existing data
DELETE FROM users;
DELETE FROM spoc_mapping;
DELETE FROM settings;

-- Insert seed users
-- Passwords are not handled here as authentication is email-based
INSERT INTO users (name, email, role) VALUES
('Adam Admin', 'admin@innovation.cgi.com', 'ADMIN'),
('Steve Spoc', 'spoc@innovation.cgi.com', 'SPOC'),
('Eva Exec', 'cgi-exec@innovation.cgi.com', 'CGI_EXEC'),
('Linda Leader', 'lt-exec@innovation.cgi.com', 'LT_EXEC'),
('Ursula User', 'user@innovation.cgi.com', 'OWNER');

-- Insert seed SPOC mappings
-- Map 'Steve Spoc' to the 'Production Services' category
INSERT INTO spoc_mapping (category, spoc_id) VALUES
('Production Services', (SELECT id FROM users WHERE email = 'spoc@innovation.cgi.com'));

-- Insert initial empty settings to ensure they exist
INSERT INTO settings (key, value) VALUES
('jira_domain', ''),
('jira_email', ''),
('jira_api_token', ''),
('jira_project_key', ''),
('smtp_username', ''),
('smtp_password', ''),
('smtp_sender_name', 'Innovation Engine'),
('spoc_notification_emails', ''),
('cgi_approval_notification_emails', '');
