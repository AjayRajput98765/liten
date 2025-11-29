from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///addtech.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    grade = db.Column(db.String(10), nullable=True)  # Class/Grade level
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Sample data for features and classes
FEATURES = [
    {
        'id': 1,
        'title': 'Digital Study Notes',
        'description': 'Comprehensive, easy-to-understand notes for effective revision.',
        'icon': 'fa-book',
        'color': 'primary'
    },
    {
        'id': 2,
        'title': 'Audio Books',
        'description': 'Learn through engaging audio lessons - perfect for auditory learners.',
        'icon': 'fa-headphones',
        'color': 'success'
    },
    {
        'id': 3,
        'title': 'Interactive Videos',
        'description': 'Cinematic video lectures that make learning fun and visual.',
        'icon': 'fa-video',
        'color': 'danger'
    },
    {
        'id': 4,
        'title': 'Gamified Learning',
        'description': 'Learn through engaging games and challenges that boost retention.',
        'icon': 'fa-gamepad',
        'color': 'warning'
    }
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
    {
        'id': 1,
        'name': 'John Doe',
        'position': 'Founder & CEO',
        'image': 'img/team-1.jpg',
        'social': {
            'facebook': 'https://facebook.com',
            'twitter': 'https://twitter.com',
            'instagram': 'https://instagram.com'
        }
    },
    {
        'id': 2,
        'name': 'Jane Smith',
        'position': 'Co-Founder & CTO',
        'image': 'img/team-2.jpg',
        'social': {
            'facebook': 'https://facebook.com',
            'twitter': 'https://twitter.com',
            'instagram': 'https://instagram.com'
        }
    },
    {
        'id': 3,
        'name': 'Mike Johnson',
        'position': 'Head of Curriculum',
        'image': 'img/team-3.jpg',
        'social': {
            'facebook': 'https://facebook.com',
            'twitter': 'https://twitter.com',
            'instagram': 'https://instagram.com'
        }
    }
]

# Routes
@app.route('/')
def index():
    # Filter classes based on user's grade if logged in
    user_classes = CLASSES
    if current_user.is_authenticated and current_user.grade:
        user_grade = int(current_user.grade)
        user_classes = [c for c in CLASSES if c['id'] == user_grade]
    
    return render_template('index.html', 
                         features=FEATURES,
                         classes=user_classes,
                         founders=FOUNDERS,
                         current_user=current_user)

@app.route('/class/<int:class_id>')
def class_details(class_id):
    cls = next((c for c in CLASSES if c['id'] == class_id), None)
    if not cls:
        return redirect(url_for('index'))
    
    # If not logged in, redirect to login
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    # Check if user's grade matches the selected class
    user_grade = int(current_user.grade) if current_user.grade else None
    
    # If user tries to access a different class, redirect to their class
    if user_grade and user_grade != class_id:
        return redirect(url_for('class_details', class_id=user_grade))
    
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('username')  # Can be email or username
        password = data.get('password')
        
        # Try to find user by email first, then by username
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User.query.filter_by(username=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        else:
            return jsonify({'success': False, 'error': 'Invalid email or password'})
    
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
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        if password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match'})
        
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'error': 'Email already exists'})
        
        # Create user with email as primary identifier
        user = User(
            username=username,
            email=email,
            grade=grade,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        # Automatically log in the user after registration
        login_user(user)
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('subjects.html', user=current_user)

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
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/newsletter/subscribe', methods=['POST'])
def subscribe_newsletter():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'})
        
        existing = NewsletterSubscriber.query.filter_by(email=email).first()
        if existing:
            return jsonify({'success': False, 'error': 'Email already subscribed'})
        
        subscriber = NewsletterSubscriber(email=email)
        db.session.add(subscriber)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Successfully subscribed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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

# Error handlers
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

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)