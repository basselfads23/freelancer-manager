from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from flask_migrate import Migrate
from datetime import datetime, timedelta, UTC, date

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freelancer_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# -----------------------
# Database Models
# -----------------------
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    hourly_rate = db.Column(db.Float, nullable=True)
    tasks = db.relationship('Task', backref='project', lazy=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    billing_type = db.Column(db.String(20), nullable=False, default='hourly')
    fixed_rate = db.Column(db.Float, nullable=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    task_name = db.Column(db.String(200), nullable=False)
    is_complete = db.Column(db.Boolean, default=False)
    # This line was in the duplicate block, now it's merged here
    time_entries = db.relationship('TimeEntry', backref='task', lazy=True, cascade="all, delete-orphan")

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    company = db.Column(db.String(100))
    notes = db.Column(db.Text)
    projects = db.relationship('Project', backref='client', lazy=True)

class TimeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    end_time = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Interval, nullable=True)

    def __repr__(self):
        return f'<TimeEntry {self.id}>'

# -----------------------
# Routes
# -----------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/projects', methods=['GET', 'POST'])
def projects():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        hourly_rate = request.form.get('hourly_rate', type=float)
        deadline_str = request.form.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        new_project = Project(
            title=title,
            description=description, hourly_rate=hourly_rate,
            client_id=request.form.get('client_id', type=int),
            deadline = deadline
        )
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('projects'))

    all_projects = Project.query.order_by(Project.id.desc()).all()
    return render_template('projects.html', projects=all_projects)

@app.route('/add_task/<int:project_id>', methods=['POST'])
def add_task(project_id):
    task_name = request.form.get('task_name')
    new_task = Task(task_name=task_name, project_id=project_id)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('projects'))

@app.route('/toggle_task/<int:task_id>')
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.is_complete = not task.is_complete
    db.session.commit()
    return redirect(url_for('projects'))

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        company = request.form.get('company')
        notes = request.form.get('notes')

        new_client = Client(name=name, email=email, company=company, notes=notes)
        db.session.add(new_client)
        db.session.commit()
        return redirect(url_for('clients'))

    all_clients = Client.query.all()
    return render_template('clients.html', clients=all_clients)

@app.route('/start_timer/<int:task_id>', methods=['POST'])
def start_timer(task_id):
    # Stop any other running timers for this user first (optional, but good practice)
    running_timer = TimeEntry.query.filter_by(task_id=task_id, end_time=None).first()
    if running_timer:
        return jsonify({'error': 'A timer is already running for this task'}), 400

    new_entry = TimeEntry(task_id=task_id)
    db.session.add(new_entry)
    db.session.commit()
    return jsonify({'success': True, 'entry_id': new_entry.id, 'start_time': new_entry.start_time.isoformat()})

@app.route('/stop_timer/<int:task_id>', methods=['POST'])
def stop_timer(task_id):
    entry = TimeEntry.query.filter_by(task_id=task_id, end_time=None).first()
    if entry:
        entry.end_time = datetime.now(UTC)
        entry.duration = entry.end_time - entry.start_time
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'No active timer found for this task'}), 404

# In app.py, add this new route

@app.route('/status_timer/<int:task_id>')
def status_timer(task_id):
    running_timer = TimeEntry.query.filter_by(task_id=task_id, end_time=None).first()
    return jsonify({'is_running': running_timer is not None})

# -----------------------
# Main
# -----------------------
if __name__ == '__main__':
    if not os.path.exists('freelancer_manager.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
