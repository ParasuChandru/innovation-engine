"""
Innovation Engine - Flask Application
Enterprise Idea Submission Workflow Management
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_cors import CORS
from functools import wraps
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'innovation-engine-secret-key-change-in-production')
CORS(app)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'innovation.db')

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

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
# Helper Functions
# ============================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Get file type category based on extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in {'pdf'}:
        return 'pdf'
    elif ext in {'doc', 'docx'}:
        return 'word'
    elif ext in {'xls', 'xlsx'}:
        return 'excel'
    elif ext in {'ppt', 'pptx'}:
        return 'powerpoint'
    elif ext in {'png', 'jpg', 'jpeg', 'gif'}:
        return 'image'
    elif ext in {'txt'}:
        return 'text'
    else:
        return 'other'

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

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
            est_cost_time, proj_savings
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        data.get('proj_savings')
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

# ============================================
# Document Management Functions
# ============================================

def get_documents_by_idea(idea_id):
    """Get all documents for an idea"""
    conn = get_db()
    documents = conn.execute('''
        SELECT 
            d.*,
            u.name as uploader_name,
            u.email as uploader_email
        FROM documents d
        JOIN users u ON d.uploaded_by = u.id
        WHERE d.idea_id = ?
        ORDER BY d.uploaded_at DESC
    ''', (idea_id,)).fetchall()
    conn.close()
    return [dict(doc) for doc in documents]

def get_document_by_id(doc_id):
    """Get a single document by ID"""
    conn = get_db()
    document = conn.execute('''
        SELECT 
            d.*,
            u.name as uploader_name,
            u.email as uploader_email
        FROM documents d
        JOIN users u ON d.uploaded_by = u.id
        WHERE d.id = ?
    ''', (doc_id,)).fetchone()
    conn.close()
    return dict(document) if document else None

def create_document(idea_id, user_id, original_filename, stored_filename, file_size, file_type, description=None):
    """Create a new document record"""
    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO documents (
            idea_id, uploaded_by, original_filename, stored_filename, 
            file_size, file_type, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (idea_id, user_id, original_filename, stored_filename, file_size, file_type, description))
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id

def delete_document(doc_id):
    """Delete a document record and file"""
    doc = get_document_by_id(doc_id)
    if doc:
        # Delete file from filesystem
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc['stored_filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete database record
        conn = get_db()
        conn.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        conn.commit()
        conn.close()
        return True
    return False

def get_document_count_by_idea(idea_id):
    """Get count of documents for an idea"""
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM documents WHERE idea_id = ?', (idea_id,)).fetchone()[0]
    conn.close()
    return count

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
            'proj_savings': float(request.form.get('proj_savings')) if request.form.get('proj_savings') else None
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
    
    # Get documents for this idea
    documents = get_documents_by_idea(idea_id)
    
    # Check if user can upload documents
    can_upload = (
        user['role'] == 'ADMIN' or
        idea['submitter_id'] == user['id'] or
        idea['spoc_id'] == user['id']
    )
    
    # Check if user can delete documents
    can_delete = user['role'] == 'ADMIN' or idea['submitter_id'] == user['id']
    
    return render_template('idea_detail.html',
        user=user,
        idea=idea,
        statuses=IDEA_STATUSES,
        current_index=current_index,
        documents=documents,
        can_upload=can_upload,
        can_delete=can_delete,
        allowed_extensions=', '.join(ALLOWED_EXTENSIONS),
        format_file_size=format_file_size
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
        (user['role'] == 'SPOC' and idea['spoc_id'] == user['id'] and 
         idea['status'] in ['Open', 'ScoreIT', 'Business Case Template']) or
        (user['role'] == 'CGI_EXEC' and idea['status'] == 'Waiting for CGI approval') or
        (user['role'] == 'LT_EXEC' and idea['status'] == 'Waiting for LT approval')
    )
    
    if can_update:
        update_idea_status(idea_id, new_status)
        flash(f'Status updated to: {new_status}', 'success')
    else:
        flash('Not authorized to update status', 'error')
    
    return redirect(url_for('idea_detail', idea_id=idea_id))

# ============================================
# Document Upload Routes
# ============================================

@app.route('/ideas/<int:idea_id>/documents/upload', methods=['POST'])
@login_required
def upload_document(idea_id):
    """Upload a document for an idea"""
    user = get_current_user()
    idea = get_idea_by_id(idea_id)
    
    if not idea:
        flash('Idea not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user can upload
    can_upload = (
        user['role'] == 'ADMIN' or
        idea['submitter_id'] == user['id'] or
        idea['spoc_id'] == user['id']
    )
    
    if not can_upload:
        flash('Not authorized to upload documents', 'error')
        return redirect(url_for('idea_detail', idea_id=idea_id))
    
    # Check if file was uploaded
    if 'document' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('idea_detail', idea_id=idea_id))
    
    file = request.files['document']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('idea_detail', idea_id=idea_id))
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        stored_filename = f"{uuid.uuid4().hex}_{idea_id}.{file_ext}"
        
        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Save file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Get file type
        file_type = get_file_type(original_filename)
        
        # Get description from form
        description = request.form.get('description', '')
        
        # Create database record
        create_document(
            idea_id=idea_id,
            user_id=user['id'],
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            file_type=file_type,
            description=description
        )
        
        flash(f'Document "{original_filename}" uploaded successfully!', 'success')
    else:
        allowed = ', '.join(ALLOWED_EXTENSIONS)
        flash(f'Invalid file type. Allowed types: {allowed}', 'error')
    
    return redirect(url_for('idea_detail', idea_id=idea_id))

@app.route('/documents/<int:doc_id>/download')
@login_required
def download_document(doc_id):
    """Download a document"""
    user = get_current_user()
    document = get_document_by_id(doc_id)
    
    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('dashboard'))
    
    idea = get_idea_by_id(document['idea_id'])
    
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
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        document['stored_filename'],
        download_name=document['original_filename'],
        as_attachment=True
    )

@app.route('/documents/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document_route(doc_id):
    """Delete a document"""
    user = get_current_user()
    document = get_document_by_id(doc_id)
    
    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('dashboard'))
    
    idea = get_idea_by_id(document['idea_id'])
    
    # Check if user can delete
    can_delete = (
        user['role'] == 'ADMIN' or
        idea['submitter_id'] == user['id'] or
        document['uploaded_by'] == user['id']
    )
    
    if not can_delete:
        flash('Not authorized to delete this document', 'error')
        return redirect(url_for('idea_detail', idea_id=document['idea_id']))
    
    if delete_document(doc_id):
        flash('Document deleted successfully', 'success')
    else:
        flash('Error deleting document', 'error')
    
    return redirect(url_for('idea_detail', idea_id=document['idea_id']))

@app.route('/kanban')
@login_required
def kanban():
    user = get_current_user()
    ideas_by_status = get_ideas_grouped_by_status()
    
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

@app.template_filter('datetime')
def datetime_filter(value):
    if value is None:
        return '-'
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y %H:%M')
    except:
        return value

@app.template_filter('filesize')
def filesize_filter(value):
    return format_file_size(value) if value else '-'

# ============================================
# Main
# ============================================

if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
