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
# Database Models (v2)
# -----------------------

# NEW: Client Model
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    # This creates a 'projects' attribute on the Client model,
    # so you can easily access all projects for a given client.
    projects = db.relationship('Project', backref='client', lazy=True)

@app.route('/delete_client/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    client_to_delete = Client.query.get_or_404(client_id)
    
    # Check if the client has any associated projects
    if client_to_delete.projects:
        flash(f'Cannot delete {client_to_delete.name}. They still have active projects.', 'danger')
    else:
        db.session.delete(client_to_delete)
        db.session.commit()
        flash(f'Client {client_to_delete.name} has been deleted.', 'success')
        
    return redirect(url_for('clients'))

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    
    # NEW: Foreign Key to link Project to Client
    # This column stores the ID of the client this project belongs to.
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)

    @property
    def days_left(self):
        if self.deadline:
            today = date.today()
            delta = self.deadline - today
            return delta.days
        return None

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
        
        # NEW: Get the client_id from the form's dropdown
        client_id = request.form.get('client_id')
        
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        new_project = Project(
            title=title,
            description=description,
            deadline=deadline,
            # NEW: Assign the client_id when creating the project
            client_id=client_id 
        )
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('projects'))

    all_projects = Project.query.order_by(Project.deadline.asc()).all()
    # NEW: Fetch all clients to pass them to the template's dropdown
    all_clients = Client.query.order_by(Client.name).all()
    
    # NEW: Pass the clients to the template
    return render_template('projects.html', projects=all_projects, clients=all_clients)

@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    project_to_delete = Project.query.get_or_404(project_id)
    db.session.delete(project_to_delete)
    db.session.commit()
    return redirect(url_for('projects'))

# -----------------------
# NEW: Client Routes
# -----------------------
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

# -----------------------
# Main
# -----------------------
if __name__ == '__main__':
    app.run(debug=True)