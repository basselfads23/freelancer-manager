from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, date

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freelancer_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# -----------------------
# Simplified Database Model
# -----------------------
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True) # This will be our "notes"
    deadline = db.Column(db.Date, nullable=True)

    # A helper property to calculate remaining days
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
        
        # Convert the deadline string from the form into a date object
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        new_project = Project(
            title=title,
            description=description,
            deadline=deadline
        )
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('projects'))

    all_projects = Project.query.order_by(Project.deadline.asc()).all()
    return render_template('projects.html', projects=all_projects)

@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    project_to_delete = Project.query.get_or_404(project_id)
    db.session.delete(project_to_delete)
    db.session.commit()
    return redirect(url_for('projects'))

# -----------------------
# Main
# -----------------------
if __name__ == '__main__':
    app.run(debug=True)