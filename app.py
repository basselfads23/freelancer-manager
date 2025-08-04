from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_migrate import Migrate
from datetime import datetime, date

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freelancer_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = r"znxyD\E_%'izc_;J**]Iow\"L£lM^f1x8vtA]:,pd)F5^}g1V=R"
db = SQLAlchemy(app)

# --- Authentication Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to login page if user is not authenticated

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# --- End of Authentication Setup ---

migrate = Migrate(app, db)

# -----------------------
# Database Models (v4)
# -----------------------

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    projects = db.relationship('Project', backref='client', lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")
    invoices = db.relationship('Invoice', backref='project', lazy=True, cascade="all, delete-orphan")

    @property
    def days_left(self):
        if self.deadline:
            today = date.today()
            delta = self.deadline - today
            return delta.days
        return None

    @property
    def completed_tasks(self):
        return Task.query.filter_by(project_id=self.id, is_completed=True).count()

    @property
    def total_tasks(self):
        return Task.query.filter_by(project_id=self.id).count()

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Draft')  # e.g., Draft, Sent, Paid
    
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    line_items = db.relationship('LineItem', backref='invoice', lazy=True, cascade="all, delete-orphan")

    @property
    def total_amount(self):
        return sum(item.amount for item in self.line_items)

class LineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)

    @property
    def amount(self):
        return self.quantity * self.unit_price

# -----------------------
# Routes
# -----------------------

@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))


@app.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    if request.method == 'POST':
        # This part for creating a project remains the same
        title = request.form.get('title')
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        client_id = request.form.get('client_id')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        new_project = Project(
            title=title,
            description=description,
            deadline=deadline,
            client_id=client_id,
            user_id=current_user.id
        )
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('projects'))

    # START MODIFICATION for handling the redirect
    # Get the new client ID from the URL arguments, if it exists
    new_client_id = request.args.get('new_client_id', type=int)

    all_projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.deadline.asc()).all()
    all_clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()

    # Pass the new client ID to the template
    return render_template('projects.html', projects=all_projects, clients=all_clients, new_client_id=new_client_id)
    # END MODIFICATION

@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):

    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    # The tasks are automatically available via the 'project.tasks' relationship we defined
    return render_template('project_detail.html', project=project)

@app.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    project_to_delete = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    db.session.delete(project_to_delete)
    db.session.commit()
    return redirect(url_for('projects'))

@app.route('/add_task/<int:project_id>', methods=['POST'])
@login_required
def add_task(project_id):

    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    
    task_description = request.form.get('task_description')
    
    if task_description:
        new_task = Task(
            description=task_description,
            project_id=project.id,
            user_id=current_user.id
        )
        db.session.add(new_task)
        db.session.commit()
        flash('New task added!', 'success')
        
    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/toggle_task/<int:task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    # Flip the boolean value
    task.is_completed = not task.is_completed
    db.session.commit()
    # Return a success response
    return {'success': True, 'is_completed': task.is_completed}

@app.route('/clients', methods=['GET', 'POST'])
@login_required
def clients():
    # Check for the 'next' argument in the URL for the GET request
    next_url = request.args.get('next')

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')

        # Check for the 'next' argument submitted with the form
        post_next_url = request.form.get('next')

        new_client = Client(name=name, email=email, user_id=current_user.id)
        db.session.add(new_client)
        db.session.commit()

        # If the form came from the projects page, redirect back there
        if post_next_url == 'projects':
            return redirect(url_for('projects', new_client_id=new_client.id))

        # Otherwise, do the default redirect
        return redirect(url_for('clients'))

    # For the GET request, pass the 'next_url' to the template
    all_clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    return render_template('clients.html', clients=all_clients, next_url=next_url)

@app.route('/delete_client/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    client_to_delete = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    
    if client_to_delete.projects:
        flash(f'Cannot delete {client_to_delete.name}. They still have active projects.', 'danger')
    else:
        db.session.delete(client_to_delete)
        db.session.commit()
        flash(f'Client {client_to_delete.name} has been deleted.', 'success')
        
    return redirect(url_for('clients'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if username already exists
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.', 'warning')
            return redirect(url_for('register'))
            
        new_user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/invoices')
@login_required
def invoices():
    all_invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.issue_date.desc()).all()
    all_projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.title).all()

    return render_template('invoices.html', invoices=all_invoices, projects=all_projects)

@app.route('/create-invoice', methods=['POST'])
@login_required
def create_invoice():
    # Get project_id from the form submission
    project_id = request.form.get('project_id')
    if not project_id:
        flash('You must select a project.', 'danger')
        return redirect(url_for('invoices'))

    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()

    # Generate a unique invoice number
    last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
    invoice_count = last_invoice.id if last_invoice else 0
    invoice_number = f'INV-{invoice_count + 1:04d}'

    new_invoice = Invoice(
        invoice_number=invoice_number,
        project_id=project.id,
        user_id=current_user.id
    )
    db.session.add(new_invoice)
    db.session.commit()

    flash(f'Invoice {invoice_number} created for project {project.title}.', 'success')
    return redirect(url_for('invoice_detail', invoice_id=new_invoice.id))

@app.route('/invoice/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    return render_template('invoice_detail.html', invoice=invoice)

@app.route('/invoice/<int:invoice_id>/add-item', methods=['POST'])
@login_required
def add_line_item(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    
    description = request.form.get('description')
    quantity = float(request.form.get('quantity', 1))
    unit_price = float(request.form.get('unit_price'))

    if description and unit_price is not None:
        new_item = LineItem(
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            invoice_id=invoice.id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Line item added.', 'success')
    else:
        flash('Description and Unit Price are required.', 'danger')
        
    return redirect(url_for('invoice_detail', invoice_id=invoice.id))

@app.route('/invoice/update-status/<int:invoice_id>', methods=['POST'])
@login_required
def update_invoice_status(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    new_status = request.form.get('status')
    due_date_str = request.form.get('due_date')

    if new_status:
        invoice.status = new_status
    
    if due_date_str:
        invoice.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()

    db.session.commit()
    flash(f'Invoice {invoice.invoice_number} has been updated.', 'success')
    return redirect(url_for('invoice_detail', invoice_id=invoice.id))

@app.route('/dashboard')
@login_required
def dashboard():
    # 1. Calculate Total Revenue (sum of all 'Paid' invoices)
    total_revenue = db.session.query(func.sum(LineItem.unit_price * LineItem.quantity)).join(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'Paid'
    ).scalar() or 0.0

    # 2. Calculate Outstanding Revenue (sum of all 'Sent' invoices)
    outstanding_revenue = db.session.query(func.sum(LineItem.unit_price * LineItem.quantity)).join(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'Sent'
    ).scalar() or 0.0
    
    # 3. Calculate Total Invoiced (sum of all invoices, regardless of status)
    total_invoiced = db.session.query(func.sum(LineItem.unit_price * LineItem.quantity)).join(Invoice).filter(
        Invoice.user_id == current_user.id
    ).scalar() or 0.0

    # 4. Calculate Revenue per Client
    revenue_by_client = db.session.query(
        Client.name,
        func.sum(LineItem.unit_price * LineItem.quantity)
    ).join(Project).join(Invoice).join(LineItem).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'Paid'
    ).group_by(Client.name).order_by(Client.name).all()

    return render_template(
        'dashboard.html',
        total_revenue=total_revenue,
        outstanding_revenue=outstanding_revenue,
        total_invoiced=total_invoiced,
        revenue_by_client=revenue_by_client
    )

# -----------------------
# Main
# -----------------------
if __name__ == '__main__':
    app.run(debug=True)