"""
Innovation Engine - Flask Application
Enterprise Idea Submission Workflow Management
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from werkzeug.utils import secure_filename
from flask_cors import CORS
from functools import wraps
import sqlite3
import os
import uuid
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from encryption import encrypt_data, decrypt_data

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

if not app.secret_key:
    raise ValueError("FATAL: SECRET_KEY not found in environment variables. Please set it in your .env file.")
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'xlsx', 'ppt', 'pptx'}
CORS(app)

# Hardcoded SMTP settings
SMTP_SERVER = "smtprelay.cgi.com"
SMTP_PORT = 587

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'innovation.db')

# Workflow statuses
IDEA_STATUSES = [
    'Open',
    'ScoreIT',
    'Business Case Template',
    'Waiting for CGI approval',
    'Waiting for LT approval',
    'Ready for implementation',
    'Implementation in progress',
    'Deploy and Done'
]

# User roles
USER_ROLES = ['OWNER', 'SPOC', 'CGI_EXEC', 'LT_EXEC', 'ADMIN']

# Categories
CATEGORIES = [
    'Production Services',
    'SAMS Ops',
    'IT Infrastructure',
    'Customer Experience',
    'Finance & Accounting',
    'Human Resources',
    'Supply Chain',
    'Marketing'
]

# ============================================
# Database Functions
# ============================================

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_email(email):
    """Get user by email"""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_spoc_by_category(category):
    """Get SPOC for a category, or default admin"""
    conn = get_db()
    result = conn.execute('''
        SELECT u.* FROM users u
        JOIN spoc_mapping sm ON u.id = sm.spoc_id
        WHERE sm.category = ?
    ''', (category,)).fetchone()
    
    if not result:
        result = conn.execute("SELECT * FROM users WHERE role = 'ADMIN' LIMIT 1").fetchone()
    
    conn.close()
    return dict(result) if result else None

def get_all_ideas():
    """Get all ideas with submitter and SPOC info"""
    conn = get_db()
    ideas = conn.execute('''
        SELECT 
            i.*,
            s.name as submitter_name,
            s.email as submitter_email,
            sp.name as spoc_name,
            sp.email as spoc_email
        FROM ideas i
        JOIN users s ON i.submitter_id = s.id
        LEFT JOIN users sp ON i.spoc_id = sp.id
        ORDER BY i.created_at DESC
    ''').fetchall()
    conn.close()
    return [dict(idea) for idea in ideas]

def get_ideas_by_submitter(submitter_id):
    """Get ideas by submitter"""
    conn = get_db()
    ideas = conn.execute('''
        SELECT 
            i.*,
            s.name as submitter_name,
            s.email as submitter_email,
            sp.name as spoc_name,
            sp.email as spoc_email
        FROM ideas i
        JOIN users s ON i.submitter_id = s.id
        LEFT JOIN users sp ON i.spoc_id = sp.id
        WHERE i.submitter_id = ?
        ORDER BY i.created_at DESC
    ''', (submitter_id,)).fetchall()
    conn.close()
    return [dict(idea) for idea in ideas]

def get_ideas_by_spoc(spoc_id):
    """Get ideas assigned to SPOC"""
    conn = get_db()
    ideas = conn.execute('''
        SELECT 
            i.*,
            s.name as submitter_name,
            s.email as submitter_email,
            sp.name as spoc_name,
            sp.email as spoc_email
        FROM ideas i
        JOIN users s ON i.submitter_id = s.id
        LEFT JOIN users sp ON i.spoc_id = sp.id
        WHERE i.spoc_id = ?
        ORDER BY i.created_at DESC
    ''', (spoc_id,)).fetchall()
    conn.close()
    return [dict(idea) for idea in ideas]

def get_ideas_by_spoc_and_status(spoc_id, status):
    """Get ideas assigned to SPOC filtered by status"""
    conn = get_db()
    ideas = conn.execute('''
        SELECT 
            i.*,
            s.name as submitter_name,
            s.email as submitter_email,
            sp.name as spoc_name,
            sp.email as spoc_email
        FROM ideas i
        JOIN users s ON i.submitter_id = s.id
        LEFT JOIN users sp ON i.spoc_id = sp.id
        WHERE i.spoc_id = ? AND i.status = ?
        ORDER BY i.created_at DESC
    ''', (spoc_id, status)).fetchall()
    conn.close()
    return [dict(idea) for idea in ideas]

def get_ideas_by_status(status):
    """Get ideas by status"""
    conn = get_db()
    ideas = conn.execute('''
        SELECT 
            i.*,
            s.name as submitter_name,
            s.email as submitter_email,
            sp.name as spoc_name,
            sp.email as spoc_email
        FROM ideas i
        JOIN users s ON i.submitter_id = s.id
        LEFT JOIN users sp ON i.spoc_id = sp.id
        WHERE i.status = ?
        ORDER BY i.created_at DESC
    ''', (status,)).fetchall()
    conn.close()
    return [dict(idea) for idea in ideas]

def get_idea_by_id(idea_id):
    """Get single idea by ID"""
    conn = get_db()
    idea = conn.execute('''
        SELECT 
            i.*,
            s.name as submitter_name,
            s.email as submitter_email,
            sp.name as spoc_name,
            sp.email as spoc_email
        FROM ideas i
        JOIN users s ON i.submitter_id = s.id
        LEFT JOIN users sp ON i.spoc_id = sp.id
        WHERE i.id = ?
    ''', (idea_id,)).fetchone()
    conn.close()
    return dict(idea) if idea else None

def create_idea(data):
    """Create a new idea"""
    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO ideas (
            title, submitter_id, spoc_id, status, category, sub_category,
            problem_statement, proposed_solution, support_needed,
            users_impacted, business_impact, complexity, tools_used,
            est_cost_time, proj_savings, hours_saved, savings_measurement,
            target_completion_date, target_pi, document_filename, document_original_filename
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['title'],
        data['submitter_id'],
        data.get('spoc_id'),
        'Open',
        data['category'],
        data.get('sub_category'),
        data['problem_statement'],
        data['proposed_solution'],
        data.get('support_needed'),
        data.get('users_impacted'),
        data.get('business_impact'),
        data.get('complexity'),
        data.get('tools_used'),
        data.get('est_cost_time'),
        data.get('proj_savings'),
        data.get('hours_saved'),
        data.get('savings_measurement'),
        data.get('target_completion_date'),
        data.get('target_pi'),
        data.get('document_filename'),
        data.get('document_original_filename')
    ))
    idea_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return idea_id

def update_idea_status(idea_id, new_status):
    """Update idea status"""
    conn = get_db()
    conn.execute('''
        UPDATE ideas 
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_status, idea_id))
    conn.commit()
    conn.close()

def update_idea_benefits(idea_id, proj_savings, hours_saved, savings_measurement, business_impact):
    """Update idea benefits fields"""
    conn = get_db()
    conn.execute('''
        UPDATE ideas 
        SET proj_savings = ?, 
            hours_saved = ?, 
            savings_measurement = ?, 
            business_impact = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (proj_savings, hours_saved, savings_measurement, business_impact, idea_id))
    conn.commit()
    conn.close()

def get_ideas_grouped_by_status():
    """Get ideas grouped by status for Kanban"""
    all_ideas = get_all_ideas()
    grouped = {status: [] for status in IDEA_STATUSES}
    for idea in all_ideas:
        if idea['status'] in grouped:
            grouped[idea['status']].append(idea)
    return grouped

def get_all_spoc_mappings():
    """Get all SPOC mappings"""
    conn = get_db()
    mappings = conn.execute('''
        SELECT sm.*, u.name as spoc_name, u.email as spoc_email
        FROM spoc_mapping sm
        JOIN users u ON sm.spoc_id = u.id
        ORDER BY sm.category
    ''').fetchall()
    conn.close()
    return [dict(m) for m in mappings]

def get_settings():
    """Get all settings from the database."""
    conn = get_db()
    settings_rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    return {row['key']: row['value'] for row in settings_rows}

def save_setting(key, value):
    """Save a setting to the database."""
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def import_spoc_mappings(mappings):
    """Clear and import SPOC mappings"""
    conn = get_db()
    conn.execute('DELETE FROM spoc_mapping')
    
    success = 0
    failed = 0
    
    for m in mappings:
        user = conn.execute(
            "SELECT id FROM users WHERE email = ? AND role IN ('SPOC', 'ADMIN')",
            (m['spoc_email'],)
        ).fetchone()
        
        if user:
            conn.execute(
                'INSERT INTO spoc_mapping (category, spoc_id) VALUES (?, ?)',
                (m['category'], user['id'])
            )
            success += 1
        else:
            failed += 1
    
    conn.commit()
    conn.close()
    return success, failed

def update_idea_jira_link(idea_id, jira_link):
    """Update an idea with the Jira ticket link."""
    conn = get_db()
    conn.execute('UPDATE ideas SET jira_ticket_link = ? WHERE id = ?', (jira_link, idea_id))
    conn.commit()
    conn.close()

# ============================================
# Email Notifications
# ============================================

def send_status_update_email(idea, new_status):
    """Sends a customized email notification for an idea status change."""
    settings = get_settings()    
    smtp_username = settings.get('smtp_username')
    smtp_password_encrypted = settings.get('smtp_password')
    smtp_sender_name = settings.get('smtp_sender_name', 'Innovation Engine')
    if not all([smtp_username, smtp_password_encrypted]):
        print(f"SMTP settings not configured. Skipping email for idea {idea['id']}.")
        return

    # Build recipient list
    recipients = {idea['submitter_email']}
    
    spoc_emails_str = settings.get('spoc_notification_emails', '')
    if spoc_emails_str:
        recipients.update([email.strip() for email in spoc_emails_str.split(',') if email.strip()])

    if new_status == 'Waiting for CGI approval':
        cgi_emails_str = settings.get('cgi_approval_notification_emails', '')
        if cgi_emails_str:
            recipients.update([email.strip() for email in cgi_emails_str.split(',') if email.strip()])

    # Remove any empty strings that might result from splitting
    recipients.discard('')
    
    recipient_list = list(recipients)
    if not recipient_list:
        print(f"No recipients found for idea {idea['id']} status update.")
        return

    smtp_password = decrypt_data(smtp_password_encrypted)
    try:
        subject = f"Innovation Idea Update: '{idea['title']}' is now {new_status}"
        body = f"""Hello Team,

An update has occurred for the innovation idea: "{idea['title']}".

Details:
- Idea Title: {idea['title']}
- New Status: {new_status}
- Submitter: {idea['submitter_name']}
- Category: {idea['category']}

You can view the latest updates here:
{url_for('idea_detail', idea_id=idea['id'], _external=True)}

Thank you,
The Innovation Engine Team
"""

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = f"{smtp_sender_name} <{smtp_username}>"
        msg['To'] = ", ".join(recipient_list)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, recipient_list, msg.as_string())
            print(f"Successfully sent status update email for idea {idea['id']} to: {', '.join(recipient_list)}")

    except Exception as e:
        # Fail silently as requested
        print(f"ERROR: Failed to send email for idea {idea['id']}. Reason: {e}")


# ============================================
# Jira Integration
# ============================================

def create_jira_ticket(idea):
    """Creates a Jira ticket for an idea."""
    settings = get_settings()
    jira_domain = settings.get('jira_domain')
    jira_email = settings.get('jira_email')   
    jira_api_token_encrypted = settings.get('jira_api_token')
    jira_project_key = settings.get('jira_project_key')

    if not all([jira_domain, jira_email, jira_api_token_encrypted, jira_project_key]):
        return None, "Jira settings are not configured."

    url = f"https://{jira_domain}/rest/api/2/issue"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "fields": {
            "project": {
                "key": jira_project_key
            },
            "summary": idea['title'],
            "description": f"h2. Problem Statement\n{idea['problem_statement']}\n\nh2. Proposed Solution\n{idea['proposed_solution']}",
            "issuetype": {
                "name": "Task"
            }
        }
    }

    try:
        jira_api_token = decrypt_data(jira_api_token_encrypted)
    except Exception:
        # Fallback in case the database still holds a plain-text token
        jira_api_token = jira_api_token_encrypted
        
    auth = (jira_email, jira_api_token)
    try:
        response = requests.post(url, json=payload, headers=headers, auth=auth)
        response.raise_for_status()
        ticket_data = response.json()
        ticket_key = ticket_data['key']
        ticket_url = f"https://{jira_domain}/browse/{ticket_key}"
        return ticket_url, None
    except requests.exceptions.RequestException as e:
        error_details = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
            except Exception:
                error_details = e.response.text
        return None, f"Jira rejected the request: {error_details}"

# ============================================
# Authentication Decorator
# ============================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged in user"""
    if 'user_id' in session:
        return get_user_by_id(session['user_id'])
    return None

# ============================================
# Routes
# ============================================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        user = get_user_by_email(email)
        
        if user:
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash('User not found. Please use a valid demo account email.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()

    if not user:
        # This can happen if the user was deleted but the session cookie remains.
        session.clear()
        flash("Your session is invalid. Please log in again.", "warning")
        return redirect(url_for('login'))
    
    # Get ideas based on role
    if user['role'] == 'OWNER':
        ideas = get_ideas_by_submitter(user['id'])
        title = "My Ideas"
        description = "Track your submitted innovation ideas"
    elif user['role'] == 'SPOC':
        ideas = get_ideas_by_spoc(user['id'])
        title = "Assigned Ideas"
        description = "Ideas assigned to you for review"
    elif user['role'] == 'CGI_EXEC':
        ideas = get_ideas_by_status('Waiting for CGI approval')
        title = "CGI Pending Approvals"
        description = "Ideas awaiting your approval"
    elif user['role'] == 'LT_EXEC':
        ideas = get_ideas_by_status('Waiting for LT approval')
        title = "LT Pending Approvals"
        description = "Ideas awaiting leadership approval"
    else:  # ADMIN
        ideas = get_all_ideas()
        title = "All Ideas"
        description = "Complete view of all innovation ideas"
    
    # Calculate stats
    total = len(ideas)
    in_progress = len([i for i in ideas if i['status'] not in ['Open', 'Deploy and Done']])
    completed = len([i for i in ideas if i['status'] == 'Deploy and Done'])
    total_savings = sum(i['proj_savings'] or 0 for i in ideas)
    
    return render_template('dashboard.html',
        user=user,
        ideas=ideas,
        title=title,
        description=description,
        stats={
            'total': total,
            'in_progress': in_progress,
            'completed': completed,
            'total_savings': total_savings
        }
    )

@app.route('/ideas/new', methods=['GET', 'POST'])
@login_required
def new_idea():
    user = get_current_user()
    
    if request.method == 'POST':
        # Get SPOC for category
        category = request.form.get('category')
        spoc = get_spoc_by_category(category)
        
        # Handle file upload
        document_filename = None
        document_original_filename = None
        if 'document' in request.files:
            file = request.files['document']
            if file.filename != '':
                if allowed_file(file.filename):
                    original_filename = secure_filename(file.filename)
                    extension = original_filename.rsplit('.', 1)[1]
                    unique_filename = f"{uuid.uuid4()}.{extension}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                    document_filename = unique_filename
                    document_original_filename = original_filename
                else:
                    flash('Invalid file type. Allowed types are: pdf, doc, docx, xlsx, ppt, pptx', 'error')
                    return redirect(request.url)

        # Create idea
        idea_data = {
            'title': request.form.get('title'),
            'submitter_id': user['id'],
            'spoc_id': spoc['id'] if spoc else None,
            'category': category,
            'sub_category': request.form.get('sub_category'),
            'problem_statement': request.form.get('problem_statement'),
            'proposed_solution': request.form.get('proposed_solution'),
            'support_needed': request.form.get('support_needed'),
            'users_impacted': request.form.get('users_impacted'),
            'business_impact': request.form.get('business_impact'),
            'complexity': request.form.get('complexity'),
            'tools_used': request.form.get('tools_used'),
            'est_cost_time': request.form.get('est_cost_time'),
            'proj_savings': float(request.form.get('proj_savings')) if request.form.get('proj_savings') else None,
            'hours_saved': float(request.form.get('hours_saved')) if request.form.get('hours_saved') else None,
            'savings_measurement': request.form.get('savings_measurement'),
            'target_completion_date': request.form.get('target_completion_date') or None,
            'target_pi': request.form.get('target_pi'),
            'document_filename': document_filename,
            'document_original_filename': document_original_filename
        }
        
        idea_id = create_idea(idea_data)
        flash(f'Idea submitted successfully! Assigned to SPOC: {spoc["name"] if spoc else "Admin"}', 'success')
        return redirect(url_for('idea_detail', idea_id=idea_id))
    
    return render_template('idea_form.html', user=user, categories=CATEGORIES)

@app.route('/ideas/<int:idea_id>')
@login_required
def idea_detail(idea_id):
    user = get_current_user()
    idea = get_idea_by_id(idea_id)
    
    if not idea:
        flash('Idea not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check access
    can_view = (
        user['role'] == 'ADMIN' or
        (user['role'] == 'OWNER' and idea['submitter_id'] == user['id']) or
        (user['role'] == 'SPOC' and idea['spoc_id'] == user['id']) or
        (user['role'] == 'CGI_EXEC' and idea['status'] == 'Waiting for CGI approval') or
        (user['role'] == 'LT_EXEC' and idea['status'] == 'Waiting for LT approval')
    )
    
    if not can_view:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get current status index for stepper
    current_index = IDEA_STATUSES.index(idea['status']) if idea['status'] in IDEA_STATUSES else 0
    
    # Calculate priority score if in ScoreIT stage
    priority_info = None
    if idea['status'] == 'ScoreIT':
        priority_info = calculate_priority_score(idea)
    
    # Determine next stage for generic advance button
    next_stage = None
    if current_index < len(IDEA_STATUSES) - 1:
        next_stage = IDEA_STATUSES[current_index + 1]

    # Decide if the generic advance button should be shown
    show_generic_advance = (
        (user['role'] == 'ADMIN' or (user['role'] == 'SPOC' and idea['spoc_id'] == user['id'])) and
        idea['status'] not in ['Waiting for CGI approval', 'Waiting for LT approval', 'Deploy and Done']
    )

    return render_template('idea_detail.html',
        user=user,
        idea=idea,
        statuses=IDEA_STATUSES,
        current_index=current_index,
        priority_info=priority_info,
        next_stage=next_stage,
        show_generic_advance=show_generic_advance
    )

@app.route('/download_document/<int:idea_id>')
@login_required
def download_document(idea_id):
    idea = get_idea_by_id(idea_id)
    if not idea or not idea['document_filename']:
        flash('Document not found.', 'error')
        return redirect(url_for('dashboard'))

    # Authorization check for downloading files
    user = get_current_user()
    can_download = (
        user['role'] == 'ADMIN' or
        idea['submitter_id'] == user['id'] or
        idea['spoc_id'] == user['id'] or
        (user['role'] == 'CGI_EXEC' and idea['status'] == 'Waiting for CGI approval') or
        (user['role'] == 'LT_EXEC' and idea['status'] == 'Waiting for LT approval')
    )

    if not can_download:
        flash('You do not have permission to download this file.', 'error')
        return redirect(url_for('dashboard'))
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        idea['document_filename'],
        as_attachment=True,
        download_name=idea['document_original_filename']
    )

@app.route('/ideas/<int:idea_id>/status', methods=['POST'])
@login_required
def update_status(idea_id):
    user = get_current_user()
    idea = get_idea_by_id(idea_id)
    new_status = request.form.get('status')
    
    if not idea or new_status not in IDEA_STATUSES:
        flash('Invalid request', 'error')
        return redirect(url_for('dashboard'))
    
    # Check authorization
    can_update = (
        user['role'] == 'ADMIN' or
        (user['role'] == 'SPOC' and idea['spoc_id'] == user['id']) or
        (user['role'] == 'CGI_EXEC' and idea['status'] == 'Waiting for CGI approval') or
        (user['role'] == 'LT_EXEC' and idea['status'] == 'Waiting for LT approval')
    )
    
    if can_update:
        update_idea_status(idea_id, new_status)
        flash(f'Status updated to: {new_status}', 'success')
        # Send email notification
        updated_idea = get_idea_by_id(idea_id)
        send_status_update_email(updated_idea, new_status)
    else:
        flash('Not authorized to update status', 'error')
    
    return redirect(url_for('idea_detail', idea_id=idea_id))

@app.route('/ideas/<int:idea_id>/create-jira-ticket', methods=['POST'])
@login_required
def create_jira_ticket_route(idea_id):
    idea = get_idea_by_id(idea_id)
    if not idea:
        flash('Idea not found.', 'error')
        return redirect(url_for('dashboard'))

    # Authorization check
    user = get_current_user()
    if user['role'] != 'ADMIN' and not (user['role'] == 'SPOC' and idea['spoc_id'] == user['id']):
        flash('You are not authorized to create a Jira ticket for this idea.', 'error')
        return redirect(url_for('idea_detail', idea_id=idea_id))

    ticket_url, error = create_jira_ticket(idea)

    if error:
        print(f"JIRA TICKET ERROR: {error}")
        flash(f'Error creating Jira ticket: {error}', 'error')
    else:
        print(f"JIRA TICKET SUCCESS: {ticket_url}")
        update_idea_jira_link(idea_id, ticket_url)
        flash(f'Successfully created Jira ticket: {ticket_url}', 'success')

    return redirect(url_for('idea_detail', idea_id=idea_id))

@app.route('/ideas/<int:idea_id>/edit-benefits', methods=['GET'])
@login_required
def edit_benefits(idea_id):
    """Edit benefits page - only for assigned SPOC and Admin"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    idea = get_idea_by_id(idea_id)
    
    if not idea:
        flash('Idea not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check authorization - only assigned SPOC or Admin can edit benefits
    can_edit = (
        user['role'] == 'ADMIN' or
        (user['role'] == 'SPOC' and idea['spoc_id'] == user['id'])
    )
    
    if not can_edit:
        flash('Access denied. Only the assigned SPOC or Admin can edit benefits.', 'error')
        return redirect(url_for('idea_detail', idea_id=idea_id))
    
    return render_template('edit_benefits.html',
        user=user,
        idea=idea
    )

@app.route('/ideas/<int:idea_id>/edit-benefits', methods=['POST'])
@login_required
def update_benefits(idea_id):
    """Update benefits - only for assigned SPOC and Admin"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    idea = get_idea_by_id(idea_id)
    
    if not idea:
        flash('Idea not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check authorization - only assigned SPOC or Admin can update benefits
    can_edit = (
        user['role'] == 'ADMIN' or
        (user['role'] == 'SPOC' and idea['spoc_id'] == user['id'])
    )
    
    if not can_edit:
        flash('Access denied. Only the assigned SPOC or Admin can edit benefits.', 'error')
        return redirect(url_for('idea_detail', idea_id=idea_id))
    
    # Get form data
    proj_savings = request.form.get('proj_savings')
    hours_saved = request.form.get('hours_saved')
    savings_measurement = request.form.get('savings_measurement')
    business_impact = request.form.get('business_impact')
    
    # Convert to appropriate types
    proj_savings = float(proj_savings) if proj_savings else None
    hours_saved = float(hours_saved) if hours_saved else None
    
    # Update database
    update_idea_benefits(idea_id, proj_savings, hours_saved, savings_measurement, business_impact)
    
    flash('Benefits updated successfully!', 'success')
    return redirect(url_for('idea_detail', idea_id=idea_id))

@app.route('/kanban')
@login_required
def kanban():
    user = get_current_user()
    ideas_by_status = get_ideas_grouped_by_status()
    
    # Calculate priority for ideas in ScoreIT
    if 'ScoreIT' in ideas_by_status:
        for idea in ideas_by_status['ScoreIT']:
            idea['priority_info'] = calculate_priority_score(idea)
    
    return render_template('kanban.html',
        user=user,
        ideas_by_status=ideas_by_status,
        statuses=IDEA_STATUSES
    )

@app.route('/cgi-dashboard')
@login_required
def cgi_dashboard():
    user = get_current_user()
    
    if user['role'] not in ['CGI_EXEC', 'ADMIN']:
        return redirect(url_for('dashboard'))
    
    ideas = get_ideas_by_status('Waiting for CGI approval')
    total_savings = sum(i['proj_savings'] or 0 for i in ideas)
    
    return render_template('cgi_dashboard.html',
        user=user,
        ideas=ideas,
        total_savings=total_savings
    )

@app.route('/lt-dashboard')
@login_required
def lt_dashboard():
    user = get_current_user()
    
    if user['role'] not in ['LT_EXEC', 'ADMIN']:
        return redirect(url_for('dashboard'))
    
    ideas = get_ideas_by_status('Waiting for LT approval')
    total_savings = sum(i['proj_savings'] or 0 for i in ideas)
    
    return render_template('lt_dashboard.html',
        user=user,
        ideas=ideas,
        total_savings=total_savings
    )

@app.route('/spoc-dashboard')
@login_required
def spoc_dashboard():
    """SPOC Dashboard - View all ideas assigned to the SPOC"""
    user = get_current_user()
    
    # Only SPOC and ADMIN can access this dashboard
    if user['role'] not in ['SPOC', 'ADMIN']:
        flash('Access denied. SPOC Dashboard is only available to SPOC users.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get ideas assigned to this SPOC
    if user['role'] == 'ADMIN':
        # Admin can see all ideas that have a SPOC assigned
        ideas = get_all_ideas()
    else:
        ideas = get_ideas_by_spoc(user['id'])
    
    # Calculate statistics
    total_assigned = len(ideas)
    in_progress = len([i for i in ideas if i['status'] not in ['Open', 'Deploy and Done']])
    completed = len([i for i in ideas if i['status'] == 'Deploy and Done'])
    pending_review = len([i for i in ideas if i['status'] in ['Open', 'ScoreIT', 'Business Case Template']])
    total_savings = sum(i['proj_savings'] or 0 for i in ideas)
    
    # Group ideas by status for quick overview
    status_counts = {}
    for idea in ideas:
        status = idea['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return render_template('spoc_dashboard.html',
        user=user,
        ideas=ideas,
        stats={
            'total_assigned': total_assigned,
            'in_progress': in_progress,
            'completed': completed,
            'pending_review': pending_review,
            'total_savings': total_savings
        },
        status_counts=status_counts,
        statuses=IDEA_STATUSES
    )

@app.route('/spoc/ideas')
@login_required
def spoc_ideas():
    """New Improved SPOC Ideas Dashboard with filtering"""
    user = get_current_user()
    
    # Only SPOC and ADMIN can access
    if user['role'] not in ['SPOC', 'ADMIN']:
        flash('Access denied. This page is only available to SPOC users.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get status filter from query params
    status_filter = request.args.get('status', None)
    
    # Get all ideas for this SPOC (for stats calculation)
    if user['role'] == 'ADMIN':
        all_spoc_ideas = get_all_ideas()
    else:
        all_spoc_ideas = get_ideas_by_spoc(user['id'])
    
    # Calculate stats from all ideas
    stats = {
        'total': len(all_spoc_ideas),
        'open': len([i for i in all_spoc_ideas if i['status'] == 'Open']),
        'in_progress': len([i for i in all_spoc_ideas if i['status'] not in ['Open', 'Deploy and Done']]),
        'completed': len([i for i in all_spoc_ideas if i['status'] == 'Deploy and Done']),
        'total_savings': sum(i['proj_savings'] or 0 for i in all_spoc_ideas)
    }
    
    # Count ideas per status for filter tabs
    status_counts = {}
    for idea in all_spoc_ideas:
        status = idea['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Filter ideas if status filter is provided
    if status_filter and status_filter in IDEA_STATUSES:
        if user['role'] == 'ADMIN':
            ideas = get_ideas_by_status(status_filter)
        else:
            ideas = get_ideas_by_spoc_and_status(user['id'], status_filter)
    else:
        ideas = all_spoc_ideas
    
    return render_template('spoc_ideas.html',
        user=user,
        ideas=ideas,
        stats=stats,
        status_counts=status_counts,
        statuses=IDEA_STATUSES,
        current_filter=status_filter
    )

@app.route('/admin')
@login_required
def admin():
    user = get_current_user()
    
    if user['role'] != 'ADMIN':
        return redirect(url_for('dashboard'))
    
    mappings = get_all_spoc_mappings()
    
    return render_template('admin.html',
        user=user,
        mappings=mappings
    )

@app.route('/admin/import', methods=['POST'])
@login_required
def admin_import():
    user = get_current_user()
    
    if user['role'] != 'ADMIN':
        return redirect(url_for('dashboard'))
    
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin'))
    
    # Parse CSV
    content = file.read().decode('utf-8')
    lines = content.strip().split('\n')
    
    if len(lines) < 2:
        flash('CSV must have header and at least one data row', 'error')
        return redirect(url_for('admin'))
    
    # Parse header
    header = [h.strip().lower() for h in lines[0].split(',')]
    try:
        cat_idx = header.index('category')
        email_idx = next(i for i, h in enumerate(header) if 'spoc' in h and 'email' in h)
    except (ValueError, StopIteration):
        flash('CSV must have "category" and "spoc_email" columns', 'error')
        return redirect(url_for('admin'))
    
    # Parse data
    mappings = []
    for line in lines[1:]:
        if line.strip():
            values = [v.strip() for v in line.split(',')]
            if len(values) > max(cat_idx, email_idx):
                mappings.append({
                    'category': values[cat_idx],
                    'spoc_email': values[email_idx]
                })
    
    success, failed = import_spoc_mappings(mappings)
    flash(f'Imported {success} mappings. {failed} failed.', 'success' if failed == 0 else 'warning')
    
    return redirect(url_for('admin'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user['role'] != 'ADMIN':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        # Sanitize Jira domain
        jira_domain = request.form.get('jira_domain', '').replace('https://', '').rstrip('/')
        save_setting('jira_domain', jira_domain)

        # Save other Jira settings
        save_setting('jira_email', request.form.get('jira_email', ''))
        
        # Encrypt and save Jira API token if a new one is provided
        new_jira_token = request.form.get('jira_api_token')
        if new_jira_token:
            save_setting('jira_api_token', encrypt_data(new_jira_token))

        save_setting('jira_project_key', request.form.get('jira_project_key', ''))

        # Save SMTP settings
        save_setting('smtp_username', request.form.get('smtp_username', ''))
        
        # Encrypt and save SMTP password if a new one is provided
        new_smtp_password = request.form.get('smtp_password')
        if new_smtp_password:
            save_setting('smtp_password', encrypt_data(new_smtp_password))

        save_setting('smtp_sender_name', request.form.get('smtp_sender_name', ''))
        
        # Save new email notification lists
        save_setting('spoc_notification_emails', request.form.get('spoc_notification_emails', ''))
        save_setting('cgi_approval_notification_emails', request.form.get('cgi_approval_notification_emails', ''))

        flash('Settings saved successfully!', 'success')
        return redirect(url_for('settings'))

    settings = get_settings()
    return render_template('settings.html', settings=settings)

@app.route('/disconnect-jira')
@login_required
@admin_required
def disconnect_jira():
    """Clear all Jira-related settings."""
    save_setting('jira_domain', '')
    save_setting('jira_email', '')
    save_setting('jira_api_token', '')
    save_setting('jira_project_key', '')
    flash('Jira integration has been disconnected.', 'success')
    return redirect(url_for('settings'))

@app.route('/api/jira/projects')
@login_required
@admin_required
def api_jira_projects():
    """Fetch available Jira projects using saved credentials."""
    settings = get_settings()
    jira_domain = settings.get('jira_domain')
    jira_email = settings.get('jira_email')
    jira_api_token_encrypted = settings.get('jira_api_token')

    if not all([jira_domain, jira_email, jira_api_token_encrypted]):
        return jsonify({'error': 'Please save your Jira domain, email, and API token first.'}), 400

    try:
        jira_api_token = decrypt_data(jira_api_token_encrypted)
    except Exception:
        jira_api_token = jira_api_token_encrypted

    url = f"https://{jira_domain}/rest/api/2/project"
    try:
        response = requests.get(url, auth=(jira_email, jira_api_token), timeout=10)
        response.raise_for_status()
        return jsonify({'projects': [{'key': p['key'], 'name': p['name']} for p in response.json()]})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch projects. Please check your Jira credentials.'}), 500

# ============================================
# Business Logic
# ============================================

def calculate_priority_score(idea):
    """Calculate priority score based on idea attributes with correct weighting."""
    score = 0
    breakdown = {}
    weights = {
        'savings': 0.35,
        'complexity': 0.25,
        'hours_saved': 0.25,
        'users_impacted': 0.15
    }

    # 1. Projected Savings (35% weight)
    savings = idea.get('proj_savings') or 0
    if savings > 100000:
        savings_score = 3
    elif savings > 50000:
        savings_score = 2
    else:
        savings_score = 1
    score += savings_score * weights['savings']
    breakdown['Projected Savings'] = f"{savings_score}/3 points"

    # 2. Complexity (25% weight)
    complexity_map = {'Low': 3, 'Medium': 2, 'High': 1}
    complexity_score = complexity_map.get(idea.get('complexity'), 1)
    score += complexity_score * weights['complexity']
    breakdown['Complexity'] = f"{complexity_score}/3 points"

    # 3. Hours Saved per Year (25% weight)
    hours_saved_yearly = idea.get('hours_saved') or 0
    if hours_saved_yearly > 1000:
        hours_score = 3
    elif hours_saved_yearly > 500:
        hours_score = 2
    else:
        hours_score = 1
    score += hours_score * weights['hours_saved']
    breakdown['Hours Saved (Yearly)'] = f"{hours_score}/3 points"

    # 4. Users Impacted (15% weight)
    users_impacted_str = idea.get('users_impacted', '0')
    users_num = 0
    try:
        if users_impacted_str:
            users_num = int(''.join(filter(str.isdigit, users_impacted_str)))
    except (ValueError, TypeError):
        users_num = 0
    
    if users_num > 50:
        users_score = 3
    elif users_num > 10:
        users_score = 2
    else:
        users_score = 1
    score += users_score * weights['users_impacted']
    breakdown['Users Impacted'] = f"{users_score}/3 points"

    # Determine priority based on weighted score
    # Max possible score is 3. A high score is > 2.0, med is > 1.0
    if score > 2.0:
        priority = 'High'
    elif score > 1.0:
        priority = 'Medium'
    else:
        priority = 'Low'
        
    return {
        'priority': priority,
        'score': round(score, 2),
        'breakdown': breakdown
    }

# ============================================
# Template Filters
# ============================================

@app.template_filter('currency')
def currency_filter(value):
    if value is None:
        return '-'
    return f"${value:,.0f}"

@app.template_filter('date')
def date_filter(value):
    if value is None:
        return '-'
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y')
    except:
        return value


# ============================================
# Main
# ============================================

if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
