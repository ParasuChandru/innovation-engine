# Innovation Engine (Python/Flask Version)

A complete enterprise idea submission workflow management system built with Python Flask, SQLite, and Tailwind CSS.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Database

```bash
python setup_db.py
```

### 3. Run the Application

```bash
python app.py
```

The application will be available at **http://localhost:5000**

---

## 🔐 Demo Login Accounts

| Role | Email | Access |
|------|-------|--------|
| **Admin** | `admin@company.com` | Full access |
| **CGI Executive** | `robert.brown@company.com` | CGI approval dashboard |
| **LT Executive** | `david.lee@company.com` | LT approval dashboard |
| **SPOC** | `sarah.johnson@company.com` | Manage assigned ideas |
| **Owner** | `john.smith@company.com` | Submit and view own ideas |

---

## ✨ Features

1. **Idea Submission Form** - Multi-stage form with all fields
2. **Automated SPOC Assignment** - Auto-assigns SPOC based on category
3. **8-Stage Workflow** - Linear progression with visual stepper
4. **Role-Based Access Control** - Different views per role
5. **CGI Executive Dashboard** - Approve/Reject buttons
6. **LT Executive Dashboard** - Final approval workflow
7. **Global Kanban Board** - All ideas by status
8. **Admin CSV Import** - Bulk update SPOC mappings

---

## 📁 Project Structure

```
innovation-engine/
├── app.py                 # Main Flask application
├── setup_db.py            # Database setup script
├── requirements.txt       # Python dependencies
├── test_app.py            # Test suite
├── data/
│   └── innovation.db      # SQLite database (generated)
└── templates/
    ├── base.html          # Base template with navbar
    ├── login.html         # Login page
    ├── dashboard.html     # Main dashboard
    ├── idea_form.html     # Idea submission form
    ├── idea_detail.html   # Idea detail with stepper
    ├── kanban.html        # Kanban board
    ├── cgi_dashboard.html # CGI executive view
    ├── lt_dashboard.html  # LT executive view
    └── admin.html         # Admin panel
```

---

## 📊 Workflow Stages

1. **Open** → New submission
2. **ScoreIT** → Initial evaluation
3. **Business Case Template** → Documentation
4. **Waiting for CGI approval** → CGI executive review
5. **Waiting for LT approval** → Leadership review
6. **Ready for implementation** → Approved
7. **Implementation in progress** → Being built
8. **Deploy and Done** → Completed

---

## 🛠️ Available Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database with sample data
python setup_db.py

# Run development server
python app.py

# Run tests
python test_app.py

# Run with gunicorn (production)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 📝 CSV Import Format

```csv
category,spoc_email
Production Services,sarah.johnson@company.com
SAMS Ops,mike.chen@company.com
IT Infrastructure,emily.davis@company.com
```

---

## 🎯 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/login` | Authentication |
| GET | `/logout` | Logout |
| GET | `/dashboard` | Main dashboard |
| GET/POST | `/ideas/new` | Create idea |
| GET | `/ideas/<id>` | Idea detail |
| POST | `/ideas/<id>/status` | Update status |
| GET | `/kanban` | Kanban board |
| GET | `/cgi-dashboard` | CGI approvals |
| GET | `/lt-dashboard` | LT approvals |
| GET | `/admin` | Admin panel |
| POST | `/admin/import` | CSV import |

---

## 🚀 Deployment

### Heroku
```bash
heroku create innovation-engine
git push heroku main
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Railway/Render
Both platforms auto-detect Python apps. Just push your code!

---

*Built with Flask, SQLite, and Tailwind CSS*