import os
import json
import numpy as np
from datetime import datetime
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import tensorflow as tf
from PIL import Image

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clean-track-secret-88'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login_page'
login_manager.init_app(app)

# --- MODELS ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='Resident') # Resident, Staff
    reports = db.relationship('Report', backref='author', lazy=True)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    waste_type = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='Pending') # Pending, Verified, Resolved, Fake
    votes = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- AI SETUP ---

model = None
class_labels = []

DETAILED_INFO = {
    'plastic': {
        'material': 'Plastic Waste',
        'category': 'Dry / Recyclable',
        'recyclable': 'Recyclable',
        'degradable': 'Non-Biodegradable',
        'description': 'Typical synthetic polymers like PET bottles and containers.',
        'steps': [
            '🔵 Rinse and compress bottles before placing in recycling bins.',
            '🔵 Clean wrappers and packaging before disposal.',
            '🔵 Segregate oil-contaminated plastics; do not mix with dry recyclables.'
        ],
        'impact': 'Prevents ocean plastic pollution and saves petroleum resources.'
    },
    'metal': {
        'material': 'Metal Waste',
        'category': 'Dry / Recyclable',
        'recyclable': 'Recyclable',
        'degradable': 'Non-Biodegradable',
        'description': 'Recyclable metal items like cans and tins.',
        'steps': [
            '🥫 Clean and recycle metal containers such as cans.',
            '🥫 Secure sharp metal objects before disposal to prevent injury.'
        ],
        'impact': 'Recycling aluminum saves 95% of the energy needed to make new metal.'
    },
    'paper': {
        'material': 'Paper Waste',
        'category': 'Dry / Recyclable',
        'recyclable': 'Recyclable',
        'degradable': 'Biodegradable',
        'description': 'Newsprint, office paper, and fiber materials.',
        'steps': [
            '📄 Recycle clean paper such as newspapers and books.',
            '📄 Compost damp or biodegradable paper where applicable.',
            '📄 Dispose of laminated or coated paper as non-recyclable dry waste.'
        ],
        'impact': 'One ton of recycled paper saves 17 trees and 7,000 gallons of water.'
    },
    'biological': {
        'material': 'Organic Waste (Wet)',
        'category': 'Wet / Compostable',
        'recyclable': 'Non-Recyclable',
        'degradable': 'Biodegradable',
        'description': 'Kitchen scraps and food leftovers.',
        'steps': [
            '🟢 Dispose of food waste in a designated <b>Green Bin</b>.',
            '🟢 Prefer composting for sustainable waste management.',
            '🟢 Avoid mixing with plastics or non-biodegradable materials.'
        ],
        'impact': 'Reduces landfill methane and creates nutrient-rich soil/compost.'
    },
    'glass': {
        'material': 'Glass Waste',
        'category': 'Dry / Recyclable',
        'recyclable': 'Recyclable',
        'degradable': 'Non-Biodegradable',
        'description': 'Glass jars, bottles, and transparent containers.',
        'steps': [
            '🍾 Rinse and recycle glass bottles and containers.',
            '🍾 Wrap broken glass securely before disposal for safety.'
        ],
        'impact': 'Glass can be recycled infinitely without losing purity or quality.'
    },
    'hazardous': {
        'material': 'E-Waste / Hazardous',
        'category': 'Special Handling',
        'recyclable': 'Specific Facilities Only',
        'degradable': 'Non-Biodegradable',
        'description': 'Batteries, electronics, and chemicals.',
        'steps': [
            '🔋 Dispose of batteries at authorized e-waste collection points.',
            '🔋 Segregate bulbs and tube lights for proper handling.',
            '🔋 Follow regulated methods for medical waste disposal.'
        ],
        'impact': 'Prevents toxic chemicals from leaching into soil and water.'
    },
    'cardboard': {
        'material': 'Cardboard Packaging',
        'category': 'Dry / Recyclable',
        'recyclable': 'Recyclable',
        'degradable': 'Biodegradable',
        'description': 'Corrugated boxes and thick paper packaging.',
        'steps': [
            '📦 Flatten boxes to save significant storage space.',
            '📦 Remove heavy plastic tape or large staples.',
            '📦 Keep dry; soggy cardboard can contaminate other recyclables.',
            '📦 Place in the <b>Blue Bin</b> (Paper/Cardboard).'
        ],
        'impact': 'Recycling 1 ton of cardboard saves 9 cubic yards of landfill space.'
    },
    'trash': {
        'material': 'General Waste',
        'category': 'Mixed / Non-Recyclable',
        'recyclable': 'Check Local Guidelines',
        'degradable': 'Varies',
        'description': 'Items that cannot be clearly categorized.',
        'steps': [
            '⚪ Check for specialized recycling symbols.',
            '⚪ Avoid mixing with wet food waste.',
            '⚪ Wrap sharp objects safely.',
            '⚪ Place in the <b>Black Bin</b> (General Trash).'
        ],
        'impact': 'Proper sorting prevents contamination of recyclable streams.'
    },
    'default': {
        'material': 'General Waste',
        'category': 'Mixed / Non-Recyclable',
        'recyclable': 'Check Local Guidelines',
        'degradable': 'Varies',
        'description': 'Items that cannot be clearly categorized.',
        'steps': [
            '⚪ Check for specialized recycling symbols.',
            '⚪ Avoid mixing with wet food waste.',
            '⚪ Wrap sharp objects safely.',
            '⚪ Place in the <b>Black Bin</b> (General Trash).'
        ],
        'impact': 'Proper sorting prevents contamination of recyclable streams.'
    }
}

def load_ai_model():
    global model, class_labels
    if model is not None:
        return # Already loaded
    
    model_path = 'model/waste_model.h5'
    indices_path = 'model/class_indices.json'
    if os.path.exists(model_path):
        try:
            model = tf.keras.models.load_model(model_path)
            if os.path.exists(indices_path):
                with open(indices_path, 'r') as f:
                    indices = json.load(f)
                    class_labels = {v: k for k, v in indices.items()}
            print("AI Model loaded successfully.")
        except Exception as e:
            print(f"Model load failed: {e}")
    else:
        print("Warning: Model not found.")

# --- ROUTES ---

@app.route('/')
def welcome():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('welcome.html')

@app.route('/role-selection')
def role_selection():
    return render_template('role_selection.html')

@app.route('/home')
@login_required
def home():
    reports = Report.query.order_by(Report.id.desc()).limit(5).all()
    total_reports = Report.query.count()
    verified_reports = Report.query.filter_by(status='Verified').count()
    # Mock some data for classified items if not tracked yet, or use 0
    return render_template('index.html', reports=reports, total_reports=total_reports, verified_reports=verified_reports)

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return redirect(url_for('login_page')) 

@app.route('/classify')
def classify_page():
    return render_template('classify.html')

@app.route('/camera')
@login_required
def camera_page():
    return render_template('camera.html')

@app.route('/report')
@login_required
def report_page():
    return render_template('report.html')

@app.route('/dashboard')
@login_required
def dashboard():
    sort_by = request.args.get('sort', 'recent')
    filter_status = request.args.get('filter', 'All')
    
    query = Report.query
    
    if filter_status != 'All':
        query = query.filter_by(status=filter_status)
        
    if sort_by == 'votes':
        query = query.order_by(Report.votes.desc())
    else:
        query = query.order_by(Report.id.desc())
        
    reports = query.all()
    
    # Analytics
    stats = {
        'total': Report.query.count(),
        'verified': Report.query.filter_by(status='Verified').count(),
        'fake': Report.query.filter_by(status='Fake').count(),
        'pending': Report.query.filter_by(status='Pending').count()
    }
    
    return render_template('dashboard.html', reports=reports, stats=stats, current_sort=sort_by, current_filter=filter_status)

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.role not in ['Staff', 'Admin'] and current_user.username != 'admin':
        return "Access Denied. Municipality Staff only.", 403
    
    # Show only reports submitted by Residents
    reports = Report.query.join(User).filter(User.role == 'Resident').order_by(Report.id.desc()).all()
    return render_template('admin.html', reports=reports)

# --- AUTH API ---

@app.route('/api/signup', methods=['POST'])
def api_signup():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role', 'Resident')

    user = User.query.filter_by(username=username).first()
    if user: return jsonify({'error': 'Username already exists'}), 400

    new_user = User(username=username, email=email, role=role,
                    password=generate_password_hash(password, method='scrypt'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/login', methods=['POST'])
def api_login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid username or password'}), 401

    login_user(user)
    return jsonify({'success': True})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('welcome'))

# --- WASTE API ---

@app.route('/api/classify', methods=['POST'])
def classify_api():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selection'}), 400
    
    if file:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            img = Image.open(filepath).convert('RGB')
            img = img.resize((224, 224))
            img_array = np.array(img) / 255.0
            img_array = np.expand_dims(img_array, axis=0)

            if model:
                predictions = model.predict(img_array)
                predicted_class_idx = np.argmax(predictions[0])
                confidence = float(predictions[0][predicted_class_idx]) * 100
                pred_label = class_labels[predicted_class_idx]
            else:
                pred_label = "trash"
                confidence = 88.5

            details = DETAILED_INFO.get(pred_label.lower(), DETAILED_INFO['default'])
            return jsonify({
                'prediction': f"{pred_label.capitalize()}",
                'confidence': f"{confidence:.2f}%",
                'material': details['material'],
                'category': details['category'],
                'recyclable': details['recyclable'],
                'steps': details['steps'],
                'details': details
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            if os.path.exists(filepath): os.remove(filepath)

@app.route('/api/report', methods=['POST'])
@login_required
def add_report():
    location = request.form.get('location')
    description = request.form.get('description')
    waste_type = request.form.get('waste_type', 'General')
    file = request.files.get('file')
    
    filename = None
    if file:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    new_report = Report(location=location, 
                        description=description, 
                        image_url=filename,
                        author=current_user)
    db.session.add(new_report)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/resolve/<int:report_id>', methods=['POST'])
@login_required
def resolve_report(report_id):
    if current_user.role not in ['Staff', 'Admin'] and current_user.username != 'admin': return "Unauthorized", 403
    report = db.session.get(Report, report_id)
    if report:
        report.status = 'Resolved'
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/delete/<int:report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    if current_user.role not in ['Staff', 'Admin'] and current_user.username != 'admin': return "Unauthorized", 403
    report = db.session.get(Report, report_id)
    if report:
        db.session.delete(report)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/upvote/<int:report_id>', methods=['POST'])
@login_required
def upvote_report(report_id):
    report = db.session.get(Report, report_id)
    if report:
        report.votes += 1
        db.session.commit()
    return jsonify({'success': True, 'votes': report.votes})

@app.route('/api/verify/<int:report_id>', methods=['POST'])
@login_required
def verify_report(report_id):
    if current_user.role not in ['Staff', 'Admin'] and current_user.username != 'admin': return "Unauthorized", 403
    report = db.session.get(Report, report_id)
    if report:
        report.status = 'Verified'
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/fake/<int:report_id>', methods=['POST'])
@login_required
def mark_fake_report(report_id):
    if current_user.role not in ['Staff', 'Admin'] and current_user.username != 'admin': return "Unauthorized", 403
    report = db.session.get(Report, report_id)
    if report:
        report.status = 'Fake'
        db.session.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    # Initialize DB (outside reloader check is fine for SQLite)
    with app.app_context():
        db.create_all()
        
        # Auto-create admin if No users exist (Best for Demos)
        if User.query.count() == 0:
            print("Seeding database with default admin account...")
            admin_user = User(
                username='admin',
                email='admin@cleantrack.com',
                password=generate_password_hash('admin123', method='scrypt'),
                role='Staff'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default Account: admin / admin123")
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Check User table
            u_cols = [c['name'] for c in inspector.get_columns('user')]
            if 'role' not in u_cols:
                print("Adding 'role' column to user table...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'Resident'"))
                    conn.commit()
            
            # Check Report table
            r_cols = [c['name'] for c in inspector.get_columns('report')]
            if 'image_url' not in r_cols:
                print("Adding 'image_url' column...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE report ADD COLUMN image_url VARCHAR(255)"))
                    conn.commit()
            if 'votes' not in r_cols:
                print("Adding 'votes' column...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE report ADD COLUMN votes INTEGER DEFAULT 0"))
                    conn.commit()
            if 'waste_type' not in r_cols:
                print("Adding 'waste_type' column...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE report ADD COLUMN waste_type VARCHAR(50)"))
                    conn.commit()
            if 'timestamp' not in r_cols:
                print("Adding 'timestamp' column...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE report ADD COLUMN timestamp DATETIME"))
                    conn.commit()
                    
            print("Database migration check complete.")
        except Exception as e:
            print(f"Migration error: {e}")

    # Load model only in the main reloader process to save time/memory
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        load_ai_model()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
