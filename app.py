from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, date

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freelancer_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "znxyD\E_%'izc_;J**]Iow\"L£lM^f1x8vtA]:,pd)F5^}g1V=R"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# -----------------------
# Database Models (v3)
# -----------------------

class Client(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    projects = db.relationship('Project', backref='client', lazy=True)

class Project(db.Model):
    # ... (add the new 'tasks' relationship and helper properties)
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    
    # NEW: Relationship to the Task model
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")

    @property
    def days_left(self):
        if self.deadline:
            today = date.today()
            delta = self.deadline - today
            return delta.days
        return None
        
    # NEW: Helper property to count completed tasks
    @property
    def completed_tasks(self):
        return Task.query.filter_by(project_id=self.id, is_completed=True).count()

    # NEW: Helper property to count all tasks
    @property
    def total_tasks(self):
        return Task.query.filter_by(project_id=self.id).count()

# NEW: Task Model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

# -----------------------
# Routes
# -----------------------
@app.route('/')
def index():
    # We'll make the projects page the main page
    return redirect(url_for('projects'))


@app.route('/projects', methods=['GET', 'POST'])
def projects():
    if request.method == 'POST':
        title = request.form.get('title')

        description = request.form.get('description')
        
        deadline_str = request.form.get('deadline')
        
        client_id = request.form.get('client_id')  
        
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        new_project = Project(
            title=title,
            description=description,
            deadline=deadline,
            client_id=client_id 
        )
        
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('projects'))

    all_projects = Project.query.order_by(Project.deadline.asc()).all()
    all_clients = Client.query.order_by(Client.name).all()

    return render_template('projects.html', projects=all_projects, clients=all_clients)

# -----------------------
# NEW: Project Detail Route
# -----------------------
@app.route('/project/<int:project_id>')
def project_detail(project_id):
    # Find the project by its ID, or return a 404 Not Found error if it doesn't exist
    project = Project.query.get_or_404(project_id)
    # The tasks are automatically available via the 'project.tasks' relationship we defined
    return render_template('project_detail.html', project=project)

@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    project_to_delete = Project.query.get_or_404(project_id)
    db.session.delete(project_to_delete)
    db.session.commit()
    return redirect(url_for('projects'))

@app.route('/add_task/<int:project_id>', methods=['POST'])
def add_task(project_id):
    # Make sure the project exists
    project = Project.query.get_or_404(project_id)
    
    task_description = request.form.get('task_description')
    
    if task_description:
        new_task = Task(
            description=task_description,
            project_id=project.id
        )
        db.session.add(new_task)
        db.session.commit()
        flash('New task added!', 'success')
        
    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/toggle_task/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    # Flip the boolean value
    task.is_completed = not task.is_completed
    db.session.commit()
    # Return a success response
    return {'success': True, 'is_completed': task.is_completed}

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        
        new_client = Client(name=name, email=email)
        db.session.add(new_client)
        db.session.commit()
        return redirect(url_for('clients'))

    all_clients = Client.query.order_by(Client.name).all()
    return render_template('clients.html', clients=all_clients)

@app.route('/delete_client/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    client_to_delete = Client.query.get_or_404(client_id)
    
    if client_to_delete.projects:
        flash(f'Cannot delete {client_to_delete.name}. They still have active projects.', 'danger')
    else:
        db.session.delete(client_to_delete)
        db.session.commit()
        flash(f'Client {client_to_delete.name} has been deleted.', 'success')
        
    return redirect(url_for('clients'))

# -----------------------
# Main
# -----------------------
if __name__ == '__main__':
    app.run(debug=True)