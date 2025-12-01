from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import func
from flask import abort
import os
import sys
import getpass
import sqlite3
from sqlalchemy.exc import OperationalError

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///addtech.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB max

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    grade = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guardian_name = db.Column(db.String(120), nullable=False)
    guardian_email = db.Column(db.String(120), nullable=False)
    child_name = db.Column(db.String(120), nullable=False)
    child_age = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NewsletterSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(512), nullable=False)
    description = db.Column(db.Text)
    grade = db.Column(db.String(10), nullable=True)
    subject = db.Column(db.String(64), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

ALLOWED_EXT = {
    'video': {'mp4', 'mkv', 'webm', 'mov', 'avi'},
    'notes': {'pdf'},
    'flashcards': {'json', 'csv'},
    'audio': {'mp3', 'wav', 'm4a', 'aac'}
}

def allowed_file(filename, content_type):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXT.get(content_type, set())

def ensure_upload_folder(path):
    os.makedirs(path, exist_ok=True)

def _ensure_db_has_subject_column():
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not uri.startswith('sqlite:///'):
        return
    db_path = uri.replace('sqlite:///', '', 1)
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.root_path, db_path)
    if not os.path.exists(db_path):
        return
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Try both lowercase and capitalized table name just in case
        cur.execute("PRAGMA table_info('content')")
        cols = [r[1] for r in cur.fetchall()]
        if not cols:
            cur.execute("PRAGMA table_info('Content')")
            cols = [r[1] for r in cur.fetchall()]
        if 'subject' not in cols:
            try:
                cur.execute("ALTER TABLE content ADD COLUMN subject TEXT")
            except sqlite3.OperationalError:
                # fallback if table name case differs
                cur.execute("ALTER TABLE Content ADD COLUMN subject TEXT")
            conn.commit()
    except Exception as e:
        print("Failed to ensure subject column:", e)
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

FEATURES = [
    {'id': 1, 'title': 'Digital Study Notes', 'description': 'Comprehensive, easy-to-understand notes for effective revision.', 'icon': 'fa-book', 'color': 'primary'},
    {'id': 2, 'title': 'Audio Books', 'description': 'Learn through engaging audio lessons - perfect for auditory learners.', 'icon': 'fa-headphones', 'color': 'success'},
    {'id': 3, 'title': 'Interactive Videos', 'description': 'Cinematic video lectures that make learning fun and visual.', 'icon': 'fa-video', 'color': 'danger'},
    {'id': 4, 'title': 'Gamified Learning', 'description': 'Learn through engaging games and challenges that boost retention.', 'icon': 'fa-gamepad', 'color': 'warning'}
]

CLASSES = [
    {'id': 1, 'name': 'Class 1', 'description': 'Foundation basics with playful learning'},
    {'id': 2, 'name': 'Class 2', 'description': 'Building core concepts through games'},
    {'id': 3, 'name': 'Class 3', 'description': 'Intermediate learning with real-world examples'},
    {'id': 4, 'name': 'Class 4', 'description': 'Advanced problem-solving skills'},
    {'id': 5, 'name': 'Class 5', 'description': 'Critical thinking and analysis'},
    {'id': 6, 'name': 'Class 6', 'description': 'Pre-secondary foundation'},
    {'id': 7, 'name': 'Class 7', 'description': 'Secondary level introduction'},
    {'id': 8, 'name': 'Class 8', 'description': 'Advanced secondary concepts'},
]

FOUNDERS = [
    {'id': 1, 'name': 'John Doe', 'position': 'Founder & CEO', 'image': 'img/team-1.jpg', 'social': {'facebook': 'https://facebook.com', 'twitter': 'https://twitter.com', 'instagram': 'https://instagram.com'}},
    {'id': 2, 'name': 'Jane Smith', 'position': 'Co-Founder & CTO', 'image': 'img/team-2.jpg', 'social': {'facebook': 'https://facebook.com', 'twitter': 'https://twitter.com', 'instagram': 'https://instagram.com'}},
    {'id': 3, 'name': 'Mike Johnson', 'position': 'Head of Curriculum', 'image': 'img/team-3.jpg', 'social': {'facebook': 'https://facebook.com', 'twitter': 'https://twitter.com', 'instagram': 'https://instagram.com'}}
]

@app.route('/')
def index():
    user_classes = CLASSES
    if current_user.is_authenticated and current_user.grade:
        try:
            user_grade = int(current_user.grade)
            user_classes = [c for c in CLASSES if c['id'] == user_grade]
        except Exception:
            user_classes = CLASSES
    return render_template('index.html', features=FEATURES, classes=user_classes, founders=FOUNDERS, current_user=current_user)

@app.route('/class/<int:class_id>')
def class_details(class_id):
    cls = next((c for c in CLASSES if c['id'] == class_id), None)
    if not cls:
        return redirect(url_for('index'))
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    user_grade = int(current_user.grade) if current_user.grade else None
    if user_grade and user_grade != class_id:
        return redirect(url_for('class_details', class_id=user_grade))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            identifier = data.get('username')
            password = data.get('password')
        else:
            identifier = request.form.get('username')
            password = request.form.get('password')

        user = None
        if identifier:
            user = User.query.filter_by(email=identifier).first()
            if not user:
                user = User.query.filter_by(username=identifier).first()

        if user and check_password_hash(user.password, password or ''):
            login_user(user)
            redirect_target = url_for('admin_panel') if user.username == 'admin' else url_for('dashboard')

            if request.is_json:
                return jsonify({'success': True, 'redirect': redirect_target})
            next_page = request.args.get('next') or request.form.get('next')
            return redirect(next_page or redirect_target)

        if request.is_json:
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401
        return render_template('login.html', error='Invalid email or password')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        grade = data.get('grade')
        if not username or not email or not password or not grade:
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        if password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'error': 'Email already exists'}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        user = User(username=username, email=email, grade=grade, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_grade = current_user.grade if getattr(current_user, 'grade', None) else None
    try:
        if user_grade:
            contents = Content.query.filter((Content.grade == None) | (Content.grade == str(user_grade))).order_by(Content.uploaded_at.desc()).all()
        else:
            contents = Content.query.order_by(Content.uploaded_at.desc()).all()
    except OperationalError as e:
        # If the DB schema is missing the subject column, try to add it and retry once
        err = str(e).lower()
        if 'no such column' in err or 'no such table' in err:
            _ensure_db_has_subject_column()
            db.session.rollback()
            if user_grade:
                contents = Content.query.filter((Content.grade == None) | (Content.grade == str(user_grade))).order_by(Content.uploaded_at.desc()).all()
            else:
                contents = Content.query.order_by(Content.uploaded_at.desc()).all()
        else:
            raise
    return render_template('Subjects.html', user=current_user, contents=contents)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    try:
        data = request.get_json()
        appointment = Appointment(
            guardian_name=data.get('guardian_name'),
            guardian_email=data.get('guardian_email'),
            child_name=data.get('child_name'),
            child_age=data.get('child_age'),
            message=data.get('message')
        )
        db.session.add(appointment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Appointment created successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/newsletter/subscribe', methods=['POST'])
def subscribe_newsletter():
    try:
        data = request.get_json()
        email = data.get('email')
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        existing = NewsletterSubscriber.query.filter_by(email=email).first()
        if existing:
            return jsonify({'success': False, 'error': 'Email already subscribed'}), 400
        subscriber = NewsletterSubscriber(email=email)
        db.session.add(subscriber)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Successfully subscribed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    users = User.query.order_by(User.created_at.desc()).all()
    appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
    subscribers = NewsletterSubscriber.query.order_by(NewsletterSubscriber.subscribed_at.desc()).all()
    contents = Content.query.order_by(Content.uploaded_at.desc()).all()
    return render_template('admin.html', users=users, appointments=appointments, subscribers=subscribers, classes=CLASSES, contents=contents, current_user=current_user)

@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    username = request.form.get('username')
    email = request.form.get('email')
    grade = request.form.get('grade')
    password = request.form.get('password')
    if not username or not email or not password:
        return redirect(url_for('admin_panel'))
    if User.query.filter((User.email == email) | (User.username == username)).first():
        return redirect(url_for('admin_panel'))
    user = User(username=username, email=email, grade=grade, password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/edit_student/<int:user_id>', methods=['POST'])
@login_required
def edit_student(user_id):
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    user = User.query.get_or_404(user_id)
    username = request.form.get('username')
    email = request.form.get('email')
    grade = request.form.get('grade')
    password = request.form.get('password')
    if username:
        user.username = username
    if email:
        user.email = email
    user.grade = grade
    if password:
        user.password = generate_password_hash(password)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/delete_student/<int:user_id>', methods=['POST'])
@login_required
def delete_student(user_id):
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    appt = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appt)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/delete_subscriber/<int:subscriber_id>', methods=['POST'])
@login_required
def delete_subscriber(subscriber_id):
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    sub = NewsletterSubscriber.query.get_or_404(subscriber_id)
    db.session.delete(sub)
    db.session.commit()
    return redirect(url_for('admin_panel'))

# ...existing code...

@app.route('/upload_content', methods=['POST'])
@login_required
def upload_content():
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    content_type = request.form.get('type')
    title = request.form.get('title')
    grade = request.form.get('grade') or None
    subject = request.form.get('subject') or None
    description = request.form.get('description')
    file = request.files.get('file')
    if not content_type or not title or not file:
        return redirect(url_for('admin_panel'))
    if not allowed_file(file.filename, content_type):
        return redirect(url_for('admin_panel'))
    target_folder = os.path.join(app.config['UPLOAD_FOLDER'], content_type)
    ensure_upload_folder(target_folder)
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    saved_name = f"{timestamp}_{filename}"
    save_path = os.path.join(target_folder, saved_name)
    file.save(save_path)

    # store forward-slash path for URLs (cross-platform)
    rel_path = f"{content_type}/{saved_name}"
    content = Content(type=content_type, title=title, filename=rel_path, description=description, grade=grade, subject=subject)
    db.session.add(content)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # normalize filename coming from URL: convert any backslashes, trim leading slashes
    safe_rel = filename.replace('\\', '/').lstrip('/')
    uploads_root = os.path.abspath(app.config['UPLOAD_FOLDER'])
    full_path = os.path.abspath(os.path.join(uploads_root, safe_rel))

    # Prevent directory traversal: full_path must be inside uploads_root
    if not (full_path == uploads_root or full_path.startswith(uploads_root + os.sep)):
        abort(404)

    if not os.path.exists(full_path):
        abort(404)

    directory, fname = os.path.split(full_path)
    return send_from_directory(directory, fname)

@app.route('/delete_content/<int:content_id>', methods=['POST'])
@login_required
def delete_content(content_id):
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    content = Content.query.get_or_404(content_id)
    try:
        # normalize stored filename and build platform-safe path
        safe_rel = (content.filename or '').replace('\\', '/').lstrip('/')
        file_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], safe_rel))
        uploads_root = os.path.abspath(app.config['UPLOAD_FOLDER'])
        if file_path.startswith(uploads_root):
            if os.path.exists(file_path):
                os.remove(file_path)
                parent_dir = os.path.dirname(file_path)
                try:
                    if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                        os.rmdir(parent_dir)
                except Exception:
                    pass
    except Exception as e:
        print(f"Failed to delete file {content.filename}: {e}")
    db.session.delete(content)
    db.session.commit()
    return redirect(url_for('admin_panel'))

# ...existing code...

@app.route('/admin/appointments')
@login_required
def view_appointments():
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
    return render_template('admin_appointments.html', appointments=appointments)

@app.route('/admin/subscribers')
@login_required
def view_subscribers():
    if current_user.username != 'admin':
        return redirect(url_for('dashboard'))
    subscribers = NewsletterSubscriber.query.order_by(NewsletterSubscriber.subscribed_at.desc()).all()
    return render_template('admin_subscribers.html', subscribers=subscribers)


@app.route('/browse/<feature>')
@login_required
def browse_feature(feature):
    feature = (feature or '').lower()
    allowed = {'video', 'audio', 'notes', 'flashcards'}
    if feature not in allowed:
        return redirect(url_for('dashboard'))

    subject = request.args.get('subject')
    user_grade = current_user.grade if getattr(current_user, 'grade', None) else None

    q = Content.query.filter_by(type=feature)
    if user_grade:
        q = q.filter((Content.grade == None) | (Content.grade == str(user_grade)))

    if subject:
        # normalize incoming subject and DB subject: lower-case, convert hyphens/underscores to spaces
        subj_norm = subject.replace('-', ' ').replace('_', ' ').strip().lower()
        db_subject_normalized = func.lower(
            func.replace(
                func.replace(func.coalesce(Content.subject, ''), '-', ' '),
                '_', ' '
            )
        )
        q = q.filter(db_subject_normalized == subj_norm)

    contents = q.order_by(Content.uploaded_at.desc()).all()
    return render_template('browse.html', contents=contents, feature=feature, subject=subject, current_user=current_user)
# ...existing code...

@app.route('/dev-login')
def dev_login():
    if not app.debug:
        return "Not allowed", 403
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', password=generate_password_hash('ChangeMe123!'))
        db.session.add(admin)
        db.session.commit()
    login_user(admin)
    return redirect(url_for('admin_panel'))

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Page not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    print(f"Server error: {error}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'success': False, 'error': 'Method not allowed'}), 405

with app.app_context():
    ensure_upload_folder(app.config['UPLOAD_FOLDER'])
    db.create_all()
    _ensure_db_has_subject_column()

def create_admin_interactive():
    username = "admin"
    email = "admin@example.com"
    if User.query.filter_by(username=username).first():
        print("Admin user already exists")
        return
    pw = getpass.getpass("Enter admin password: ")
    if not pw:
        print("No password entered — aborting.")
        return
    u = User(username=username, email=email, password=generate_password_hash(pw))
    db.session.add(u)
    db.session.commit()
    print(f"Created admin: {username} / {email}")

if __name__ == '__main__':
    if '--create-admin' in sys.argv:
        with app.app_context():
            create_admin_interactive()
    else:
        app.run(debug=True, host='127.0.0.1', port=5000)