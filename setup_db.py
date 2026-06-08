#!/usr/bin/env python3
"""
Innovation Engine - Database Setup Script
Creates tables and seeds sample data
"""

import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'innovation.db')

def setup_database():
    """Create database schema"""
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # Create tables
    cursor.executescript('''
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('OWNER', 'SPOC', 'CGI_EXEC', 'LT_EXEC', 'ADMIN')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- SPOC Mapping table
        CREATE TABLE IF NOT EXISTS spoc_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL UNIQUE,
            spoc_id INTEGER NOT NULL,
            FOREIGN KEY (spoc_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- Settings table
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        -- Ideas table
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            submitter_id INTEGER NOT NULL,
            spoc_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN (
                'Open', 
                'ScoreIT', 
                'Business Case Template', 
                'Waiting for CGI approval', 
                'Waiting for LT approval', 
                'Ready for implementation', 
                'Implementation in progress', 
                'Deploy and Done'
            )),
            category TEXT NOT NULL,
            sub_category TEXT,
            problem_statement TEXT NOT NULL,
            proposed_solution TEXT NOT NULL,
            support_needed TEXT,
            users_impacted TEXT,
            business_impact TEXT,
            complexity TEXT CHECK(complexity IN ('Low', 'Medium', 'High')),
            tools_used TEXT,
            est_cost_time TEXT,
            proj_savings REAL,
            hours_saved REAL,
            savings_measurement TEXT,
            document_filename TEXT,
            document_original_filename TEXT,
            target_completion_date TEXT,
            target_pi TEXT,
            jira_ticket_link TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (submitter_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (spoc_id) REFERENCES users(id) ON DELETE SET NULL
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
        CREATE INDEX IF NOT EXISTS idx_ideas_submitter ON ideas(submitter_id);
        CREATE INDEX IF NOT EXISTS idx_ideas_spoc ON ideas(spoc_id);
        CREATE INDEX IF NOT EXISTS idx_ideas_category ON ideas(category);
        CREATE INDEX IF NOT EXISTS idx_spoc_mapping_category ON spoc_mapping(category);
    ''')
    
    conn.commit()
    conn.close()
    
    print('✅ Database schema created successfully!')
    print(f'   Database location: {DB_PATH}')

def migrate_database():
    """Add new columns to existing database if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if hours_saved column exists
    cursor.execute("PRAGMA table_info(ideas)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'hours_saved' not in columns:
        print('Adding hours_saved column...')
        cursor.execute('ALTER TABLE ideas ADD COLUMN hours_saved REAL')
    
    if 'savings_measurement' not in columns:
        print('Adding savings_measurement column...')
        cursor.execute('ALTER TABLE ideas ADD COLUMN savings_measurement TEXT')
        
    if 'document_filename' not in columns:
        print('Adding document_filename column...')
        cursor.execute('ALTER TABLE ideas ADD COLUMN document_filename TEXT')
        
    if 'document_original_filename' not in columns:
        print('Adding document_original_filename column...')
        cursor.execute('ALTER TABLE ideas ADD COLUMN document_original_filename TEXT')

    if 'target_completion_date' not in columns:
        print('Adding target_completion_date column...')
        cursor.execute('ALTER TABLE ideas ADD COLUMN target_completion_date TEXT')
        
    if 'target_pi' not in columns:
        print('Adding target_pi column...')
        cursor.execute('ALTER TABLE ideas ADD COLUMN target_pi TEXT')

    if 'jira_ticket_link' not in columns:
        print('Adding jira_ticket_link column...')
        cursor.execute('ALTER TABLE ideas ADD COLUMN jira_ticket_link TEXT')

    if 'confidence' not in columns:
        print('Adding confidence column...')
        cursor.execute("ALTER TABLE ideas ADD COLUMN confidence TEXT CHECK(confidence IN ('High', 'Medium', 'Low')) DEFAULT 'Medium'")

    bc_fields = [
        ('executive_summary', 'TEXT'),
        ('benefit_type', 'TEXT'),
        ('milestone_1', 'TEXT'),
        ('milestone_2', 'TEXT'),
        ('milestone_3', 'TEXT'),
        ('milestone_4', 'TEXT'),
        ('risk_assessment', 'TEXT'),
        ('mitigation_strategy', 'TEXT'),
        ('kpis', 'TEXT'),
        ('stakeholders', 'TEXT'),
        ('business_case_last_updated', 'TIMESTAMP'),
    ]
    for col_name, col_type in bc_fields:
        if col_name not in columns:
            print(f'Adding business case column: {col_name}...')
            cursor.execute(f'ALTER TABLE ideas ADD COLUMN {col_name} {col_type}')

    conn.commit()
    conn.close()
    print('✅ Database migration complete!')

def seed_database():
    """Seed database with sample data"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute('DELETE FROM ideas')
    cursor.execute('DELETE FROM spoc_mapping')
    cursor.execute('DELETE FROM users')
    
    # Insert users
    users = [
        ('Admin User', 'admin@company.com', 'ADMIN'),
        ('Sarah Johnson', 'sarah.johnson@company.com', 'SPOC'),
        ('Mike Chen', 'mike.chen@company.com', 'SPOC'),
        ('Emily Davis', 'emily.davis@company.com', 'SPOC'),
        ('James Wilson', 'james.wilson@company.com', 'SPOC'),
        ('Robert Brown', 'robert.brown@company.com', 'CGI_EXEC'),
        ('Lisa Martinez', 'lisa.martinez@company.com', 'CGI_EXEC'),
        ('David Lee', 'david.lee@company.com', 'LT_EXEC'),
        ('Jennifer Taylor', 'jennifer.taylor@company.com', 'LT_EXEC'),
        ('John Smith', 'john.smith@company.com', 'OWNER'),
        ('Anna Garcia', 'anna.garcia@company.com', 'OWNER'),
        ('Tom Harris', 'tom.harris@company.com', 'OWNER'),
        ('Nancy White', 'nancy.white@company.com', 'OWNER'),
    ]
    
    cursor.executemany(
        'INSERT INTO users (name, email, role) VALUES (?, ?, ?)',
        users
    )
    
    # Get user IDs
    user_ids = {}
    for row in cursor.execute('SELECT id, email FROM users'):
        user_ids[row[1]] = row[0]
    
    print(f'✅ Inserted {len(users)} users')
    
    # Insert SPOC mappings
    spoc_mappings = [
        ('Production Services', user_ids['sarah.johnson@company.com']),
        ('SAMS Ops', user_ids['mike.chen@company.com']),
        ('IT Infrastructure', user_ids['emily.davis@company.com']),
        ('Customer Experience', user_ids['james.wilson@company.com']),
        ('Finance & Accounting', user_ids['sarah.johnson@company.com']),
        ('Human Resources', user_ids['mike.chen@company.com']),
        ('Supply Chain', user_ids['emily.davis@company.com']),
        ('Marketing', user_ids['james.wilson@company.com']),
    ]
    
    cursor.executemany(
        'INSERT INTO spoc_mapping (category, spoc_id) VALUES (?, ?)',
        spoc_mappings
    )
    
    print(f'✅ Inserted {len(spoc_mappings)} SPOC mappings')
    
    # Insert sample ideas (with hours_saved, savings_measurement, and confidence)
    ideas = [
        ('Automated Report Generation', user_ids['john.smith@company.com'],
         user_ids['sarah.johnson@company.com'], 'Open', 'Production Services', 'Reporting',
         'Manual report generation takes 4 hours daily',
         'Implement automated reporting using Python scripts and scheduled tasks',
         'IT team support for server access', '25 analysts',
         'High - reduces manual effort significantly', 'Medium',
         'Python, Power BI', '2 months, $5000', 50000, 80, 'Time tracking before/after automation', 'Medium'),

        ('Customer Feedback AI Analysis', user_ids['anna.garcia@company.com'],
         user_ids['james.wilson@company.com'], 'Waiting for CGI approval', 'Customer Experience', 'Analytics',
         'Cannot analyze large volumes of customer feedback efficiently',
         'Deploy NLP-based sentiment analysis tool',
         'Data Science team, Cloud infrastructure', 'Customer Service team (40 people)',
         'High - improves customer satisfaction metrics', 'High',
         'Python, TensorFlow, AWS', '4 months, $25000', 120000, 160, 'Customer satisfaction score improvement', 'High'),

        ('Invoice Processing Automation', user_ids['tom.harris@company.com'],
         user_ids['sarah.johnson@company.com'], 'Waiting for CGI approval', 'Finance & Accounting', 'AP Automation',
         'Manual invoice processing leads to errors and delays',
         'OCR-based invoice scanning and auto-matching system',
         'Finance team validation, IT integration support', 'Finance department (15 people)',
         'Medium - reduces processing time by 60%', 'Medium',
         'UiPath, SAP integration', '3 months, $15000', 75000, 120, 'Processing time reduction and error rate', 'Medium'),

        ('Employee Onboarding Portal', user_ids['nancy.white@company.com'],
         user_ids['mike.chen@company.com'], 'Waiting for LT approval', 'Human Resources', 'Employee Experience',
         'Onboarding process is fragmented across multiple systems',
         'Unified self-service onboarding portal with document management',
         'HR team, IT security review', '500+ new hires annually',
         'Medium - improves new hire experience', 'Medium',
         'React, Node.js, SharePoint', '4 months, $30000', 45000, 40, 'Onboarding completion time and satisfaction surveys', 'Medium'),

        ('Inventory Tracking IoT System', user_ids['john.smith@company.com'],
         user_ids['emily.davis@company.com'], 'Ready for implementation', 'Supply Chain', 'Inventory Management',
         'Cannot track real-time inventory levels accurately',
         'IoT sensors with real-time dashboard',
         'Operations team, IoT vendor', 'Warehouse team (30 people)',
         'High - prevents stockouts and overstock', 'High',
         'IoT sensors, Azure IoT Hub, Power BI', '6 months, $50000', 200000, 200, 'Inventory accuracy and stockout incidents', 'High'),

        ('Marketing Campaign Analytics', user_ids['anna.garcia@company.com'],
         user_ids['james.wilson@company.com'], 'Implementation in progress', 'Marketing', 'Analytics',
         'Difficult to measure ROI across marketing channels',
         'Unified analytics dashboard with attribution modeling',
         'Marketing team, Data team', 'Marketing team (20 people)',
         'High - optimizes marketing spend', 'Medium',
         'Google Analytics, Tableau, Python', '3 months, $20000', 80000, 60, 'Marketing ROI and attribution accuracy', 'Medium'),

        ('Server Monitoring Automation', user_ids['tom.harris@company.com'],
         user_ids['emily.davis@company.com'], 'Deploy and Done', 'IT Infrastructure', 'DevOps',
         'Manual server health checks miss critical issues',
         'Automated monitoring with alerting system',
         'IT Ops team', 'IT team (10 people)',
         'High - prevents downtime', 'Low',
         'Prometheus, Grafana, PagerDuty', '1 month, $5000', 30000, 100, 'Downtime reduction and incident response time', 'Low'),

        ('Contract Management System', user_ids['nancy.white@company.com'],
         user_ids['sarah.johnson@company.com'], 'ScoreIT', 'Production Services', 'Legal',
         'Contract renewals often missed, leading to unfavorable terms',
         'Digital contract repository with renewal alerts',
         'Legal team, IT team', 'Legal and Procurement (25 people)',
         'Medium - ensures timely renewals', 'Medium',
         'DocuSign, SharePoint', '2 months, $10000', 35000, 30, 'Missed renewal rate and negotiation savings', 'Medium'),

        # Business Case Template — fully filled out example
        ('Fleet Telematics Optimization', user_ids['john.smith@company.com'],
         user_ids['emily.davis@company.com'], 'Business Case Template', 'Supply Chain', 'Fleet Management',
         'Our fleet of 200 vehicles wastes an estimated 15% of fuel through idle time, inefficient routing, and lack of real-time monitoring. Annual fuel costs exceed $1.2M with no visibility into driver behavior.',
         'Deploy IoT telematics devices on all vehicles with a cloud dashboard for real-time monitoring, automated routing, driver scoring, and maintenance alerts. Integrate with existing ERP for unified cost tracking.',
         'IT for integration, Fleet Ops for rollout, Vendor for device supply', '300+ drivers and fleet managers',
         'High - direct cost reduction and safety improvement', 'Medium',
         'IoT sensors, Azure IoT Hub, Power BI, REST APIs', '4 months, $80000', 200000, 2400, 'Fuel cost reduction %, on-time delivery rate, incident rate per 100k miles', 'High'),
    ]

    cursor.executemany('''
        INSERT INTO ideas (
            title, submitter_id, spoc_id, status, category, sub_category,
            problem_statement, proposed_solution, support_needed,
            users_impacted, business_impact, complexity, tools_used,
            est_cost_time, proj_savings, hours_saved, savings_measurement,
            confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ideas)

    print(f'✅ Inserted {len(ideas)} sample ideas')

    # Seed business case data for the Fleet Telematics idea (id 9)
    cursor.execute('''
        UPDATE ideas SET
            executive_summary = 'IoT telematics deployment will reduce fuel costs by 15% through idle-time elimination, route optimization, and driver behavior coaching. Estimated annual savings of $200K against an $80K investment.',
            benefit_type = 'Cost Reduction',
            milestone_1 = 'Vendor selection and contract signed by Week 6',
            milestone_2 = 'Pilot devices installed on 50 vehicles by Month 2',
            milestone_3 = 'Full fleet deployment and ERP integration by Month 4',
            milestone_4 = 'Post-implementation review and KPI baseline by Month 5',
            risk_assessment = 'Vendor delivery delays; data integration complexity with legacy ERP; driver pushback on monitoring; upfront hardware cost overrun.',
            mitigation_strategy = 'Dual-vendor shortlist with SLA penalties; early API spike by IT team; driver engagement workshops; 15% hardware contingency budget.',
            kpis = '1. Fuel cost reduction >= 12% within 6 months\\n2. On-time delivery rate > 95%\\n3. Idle-time reduction >= 20%\\n4. Incident rate < 0.5 per 100k miles',
            stakeholders = 'Fleet Operations Director (sponsor), IT Integration Lead (technical), CFO (budget), Vendor PM (delivery), Union Rep (driver concerns)',
            business_case_last_updated = CURRENT_TIMESTAMP
        WHERE title = 'Fleet Telematics Optimization'
    ''')

    conn.commit()
    conn.close()

    print('')
    print('🎉 Database seeded successfully!')
    print('')
    print('Sample login emails:')
    print('  - Admin: admin@company.com')
    print('  - CGI Exec: robert.brown@company.com')
    print('  - LT Exec: david.lee@company.com')
    print('  - SPOC: sarah.johnson@company.com')
    print('  - Owner: john.smith@company.com')

if __name__ == '__main__':
    setup_database()
    migrate_database()
    seed_database()
