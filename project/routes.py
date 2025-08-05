# project/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from datetime import datetime, date
import os
import secrets
from weasyprint import HTML

# Import extensions and models
from .extensions import db, oauth
from .models import User, Client, Project, Task, TimeEntry, Invoice, LineItem, InvoiceSequence

# Create a Blueprint
main = Blueprint('main', __name__)

# -----------------------
# Routes
# -----------------------

@main.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

@main.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    if request.method == 'POST':
        # --- Get common form data ---
        title = request.form.get('title')
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        client_id = request.form.get('client_id')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
        
        # --- Get NEW billing form data ---
        billing_type = request.form.get('billing_type')
        hourly_rate = request.form.get('hourly_rate')
        flat_fee_amount = request.form.get('flat_fee_amount')

        # --- Create new project object ---
        new_project = Project(
            title=title,
            description=description,
            deadline=deadline,
            client_id=client_id,
            user_id=current_user.id,
            billing_type=billing_type
        )
        
        # --- Set billing values based on type ---
        if billing_type == 'Hourly':
            new_project.hourly_rate = float(hourly_rate) if hourly_rate else 0.0
        elif billing_type == 'Flat Fee':
            new_project.flat_fee_amount = float(flat_fee_amount) if flat_fee_amount else 0.0

        db.session.add(new_project)
        db.session.commit()
        flash(f'Project "{title}" created successfully.', 'success')
        return redirect(url_for('project_detail', project_id=new_project.id))

    # This part handles the GET request (loading the page)
    new_client_id = request.args.get('new_client_id', type=int)
    all_projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.deadline.asc()).all()
    all_clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()

    return render_template('projects.html', projects=all_projects, clients=all_clients, new_client_id=new_client_id)

@main.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):

    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    # The tasks are automatically available via the 'project.tasks' relationship we defined
    return render_template('project_detail.html', project=project, date=date)

@main.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    project_to_delete = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    db.session.delete(project_to_delete)
    db.session.commit()
    return redirect(url_for('projects'))

@main.route('/project/<int:project_id>/update-details', methods=['POST'])
@login_required
def update_project_details(project_id):
    """ Handles updating core project details via AJAX, like the title. """
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    
    data = request.get_json()
    new_title = data.get('project_title')

    if not new_title:
        return {'success': False, 'message': 'Title cannot be empty.'}, 400

    project.title = new_title
    db.session.commit()
    
    return {'success': True, 'new_title': project.title}

# --- REPLACE the old 'add_task' function with this new version ---
@main.route('/add_task/<int:project_id>', methods=['POST'])
@login_required
def add_task(project_id):
    """
    Handles adding a new task to a project, including its
    billing details which are determined by the project's billing type.
    """
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    task_description = request.form.get('task_description')
    
    if not task_description:
        flash('Task description cannot be empty.', 'warning')
        return redirect(url_for('project_detail', project_id=project.id))

    # Create the new task with its description
    new_task = Task(
        description=task_description,
        project_id=project.id,
        user_id=current_user.id
    )

    # Add billing details based on the project's type
    if project.billing_type == 'Hourly':
        override_rate = request.form.get('override_rate')
        # Only save the override rate if the user actually entered one
        if override_rate:
            new_task.override_rate = float(override_rate)

    elif project.billing_type == 'Per Task':
        task_fee = request.form.get('task_fee')
        quantity = request.form.get('quantity', 1) # Default to 1 if not provided
        
        if task_fee:
            new_task.task_fee = float(task_fee)
        new_task.quantity = int(quantity)
        new_task.quantity_is_na = 'quantity_is_na' in request.form

    # Add the new task to the database session and commit
    db.session.add(new_task)
    db.session.commit()
    flash('New task added!', 'success')
        
    return redirect(url_for('project_detail', project_id=project.id))

@main.route('/toggle_task/<int:task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    """
    Handles toggling the completion status of a single task.
    This is called by a JavaScript fetch request.
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    # Flip the boolean value
    task.is_completed = not task.is_completed
    db.session.commit()
    # Return a JSON response for the JavaScript to read
    return {'success': True, 'is_completed': task.is_completed}

# --- ROUTE to handle deleting a task ---
@main.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    """ Handles the deletion of a single task. """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    flash('Task has been deleted.', 'success')
    return redirect(url_for('project_detail', project_id=project_id))

# --- to handle deleting a time entry ---
@main.route('/time-entry/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_time_entry(entry_id):
    """ Handles the deletion of a single time entry. """
    entry = TimeEntry.query.get_or_404(entry_id)
    
    # Security check: ensure the entry belongs to a task owned by the current user
    if entry.task.user_id != current_user.id:
        flash('You are not authorized to delete this entry.', 'danger')
        return redirect(url_for('projects'))

    project_id = entry.task.project_id
    db.session.delete(entry)
    db.session.commit()
    flash('Time entry has been deleted.', 'success')
    return redirect(url_for('project_detail', project_id=project_id))

# --- UNIFIED ROUTE for updating all task details ---
@main.route('/task/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    """
    A single route to handle all updates for a task, including
    description, billing details, and other properties.
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()

    # Update the task's description
    task.description = request.form.get('description')

    # Update billing details based on the project type
    if task.project.billing_type == 'Hourly':
        # Allow setting the override_rate to empty, which means use project default
        override_rate = request.form.get('override_rate')
        task.override_rate = float(override_rate) if override_rate else None

    elif task.project.billing_type == 'Per Task':
        task.task_fee = float(request.form.get('task_fee'))
        task.quantity = int(request.form.get('quantity'))
        task.quantity_is_na = 'quantity_is_na' in request.form

    db.session.commit()
    flash(f'Task "{task.description}" has been updated.', 'success')
    return redirect(url_for('project_detail', project_id=task.project_id))

@main.route('/clients', methods=['GET', 'POST'])
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

@main.route('/delete_client/<int:client_id>', methods=['POST'])
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

@main.route('/login', methods=['GET', 'POST'])
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

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # --- Start Validation ---
        # Check if username or email already exists
        user_by_username = User.query.filter_by(username=username).first()
        if user_by_username:
            flash('Username already exists. Please choose another.', 'warning')
            return redirect(url_for('register'))

        user_by_email = User.query.filter_by(email=email).first()
        if user_by_email:
            flash('Email address is already registered. Please log in.', 'warning')
            return redirect(url_for('login'))

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('register'))
        # --- End Validation ---
            
        new_user = User(
            username=username, 
            email=email, 
            password=generate_password_hash(password, method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@main.route('/invoices')
@login_required
def invoices():
    all_invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.issue_date.desc()).all()
    all_projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.title).all()

    return render_template('invoices.html', invoices=all_invoices, projects=all_projects)

@main.route('/create-invoice', methods=['POST'])
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

@main.route('/invoice/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    return render_template('invoice_detail.html', invoice=invoice)

@main.route('/invoice/<int:invoice_id>/add-item', methods=['POST'])
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

@main.route('/invoice/update-status/<int:invoice_id>', methods=['POST'])
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
    return redirect(url_for('invoices'))

@main.route('/dashboard')
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

@main.route('/project/<int:project_id>/save-notes', methods=['POST'])
@login_required
def save_notes(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    
    notes_content = request.form.get('notes')
    project.notes = notes_content
    
    db.session.commit()
    
    flash('Project notes have been saved.', 'success')
    return redirect(url_for('project_detail', project_id=project.id))

@main.route('/login/google')
def google_login():

    # Generate a nonce for OIDC to prevent replay attacks
    nonce = secrets.token_urlsafe(16)
    session['oauth_nonce'] = nonce

    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)

@main.route('/login/google/callback')
def google_callback():
    token = google.authorize_access_token()

    # Retrieve and remove nonce from session
    nonce = session.pop('oauth_nonce', None)

    # Parse the ID token securely using the nonce
    user_info = google.parse_id_token(token, nonce=nonce)

    if not user_info:
        flash('Google login failed: unable to fetch user info.', 'danger')
        return redirect(url_for('login'))

    # Check if the user already exists in our database
    user = User.query.filter_by(email=user_info['email']).first()

    if not user:
        new_user = User(
            username=user_info['name'].replace(" ", "").lower(),
            email=user_info['email'],
            password=generate_password_hash(os.urandom(16).hex(), method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        user = new_user

    login_user(user)
    flash('You have been successfully logged in with Google.', 'success')
    return redirect(url_for('dashboard'))

@main.route('/invoice/<int:invoice_id>/download-pdf')
@login_required
def download_pdf(invoice_id):
    # 1. Fetch the correct invoice from the database
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()

    # 2. Render our dedicated PDF template with the invoice data
    rendered_html = render_template('invoice_pdf.html', invoice=invoice)

    # 3. Use WeasyPrint to generate a PDF from the rendered HTML
    pdf = HTML(string=rendered_html).write_pdf()

    # 4. Create a Flask response to send the PDF to the user
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Invoice-{invoice.invoice_number}.pdf'

    return response

# NEW ROUTES FOR TIME TRACKING
# --- REPLACEED the old 'log_time' function with this new AJAX-ready version ---
@main.route('/task/<int:task_id>/log-time', methods=['POST'])
@login_required
def log_time(task_id):
    """ Handles logging a new time entry for a task via an AJAX request. """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    if task.project.billing_type != 'Hourly':
        # Return an error as JSON
        return {'success': False, 'message': 'Time can only be logged for hourly projects.'}, 400

    hours_worked = request.form.get('hours_worked')
    entry_date_str = request.form.get('entry_date')

    if not hours_worked:
        return {'success': False, 'message': 'Please enter the number of hours worked.'}, 400

    new_entry = TimeEntry(
        hours_worked=float(hours_worked),
        entry_date=datetime.strptime(entry_date_str, '%Y-%m-%d').date() if entry_date_str else date.today(),
        task_id=task.id
    )
    db.session.add(new_entry)
    db.session.commit()

    # Return the new entry's data and the new total hours as JSON
    return {
        'success': True,
        'entry': {
            'id': new_entry.id,
            'hours': new_entry.hours_worked,
            'date': new_entry.entry_date.strftime('%Y-%m-%d')
        },
        'total_hours': task.total_hours_logged
    }

@main.route('/task/<int:task_id>/quick-log', methods=['POST'])
@login_required
def quick_log_time(task_id):
    # This is a simplified "timer" - for now, it just logs a preset amount of time.
    # We can make this a real start/stop timer later if needed.
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    if task.project.billing_type != 'Hourly':
        # This check is important for security
        return {'success': False, 'message': 'Time can only be logged for hourly projects.'}

    # For this example, a "quick log" adds 15 minutes (0.25 hours)
    new_entry = TimeEntry(hours_worked=0.25, task_id=task.id)
    db.session.add(new_entry)
    db.session.commit()
    
    return {'success': True, 'total_hours': task.total_hours_logged}

@main.route('/task/<int:task_id>/update-billing', methods=['POST'])
@login_required
def update_task_billing(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    # Ensure the project is a Per Task project
    if task.project.billing_type != 'Per Task':
        flash('Task billing can only be updated for "Per Task" projects.', 'danger')
        return redirect(url_for('project_detail', project_id=task.project_id))

    task_fee = request.form.get('task_fee')
    quantity = request.form.get('quantity')
    
    # Update values if they are provided in the form
    if task_fee:
        task.task_fee = float(task_fee)
    if quantity:
        task.quantity = int(quantity)

    db.session.commit()
    flash(f'Billing details for task "{task.description}" have been updated.', 'success')
    return redirect(url_for('project_detail', project_id=task.project_id))

# --- ROUTE FOR SMART INVOICE GENERATION ---
@main.route('/project/<int:project_id>/generate-invoice', methods=['POST'])
@login_required
def generate_invoice(project_id):
    """
    Generates a new invoice from all completed, unbilled tasks for a project.
    This version is production-grade, handling race conditions and edge cases.
    """
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()

    # With SQLite's default transaction isolation, the entire database is locked
    # on write, which prevents race conditions for this operation.
    try:
        # Step 1: Find all tasks that are ready to be billed.
        tasks_to_bill = Task.query.filter_by(
            project_id=project.id,
            is_completed=True,
            is_billable=True,
            has_been_billed=False
        ).all()

        if not tasks_to_bill:
            flash('No completed, unbilled tasks are available to invoice.', 'warning')
            return redirect(url_for('project_detail', project_id=project.id))

        # Step 2: Pre-process tasks to generate potential line items.
        line_items_to_create = []
        if project.billing_type == 'Flat Fee':
            tasks_summary = '; '.join([task.description for task in tasks_to_bill])
            if len(tasks_summary) > 195:
                tasks_summary = tasks_summary[:195] + '...'
            
            line_items_to_create.append({
                'description': f'Project: {project.title} - {tasks_summary}',
                'quantity': 1,
                'unit_price': project.flat_fee_amount or 0.0,
                'tasks_to_link': tasks_to_bill # Link all tasks to this one item
            })

        elif project.billing_type == 'Hourly':
            for task in tasks_to_bill:
                if task.total_hours_logged > 0:
                    rate = task.override_rate or project.hourly_rate or 0.0
                    line_items_to_create.append({
                        'description': task.description,
                        'quantity': task.total_hours_logged,
                        'unit_price': rate,
                        'tasks_to_link': [task] # Link one task to this item
                    })

        elif project.billing_type == 'Per Task':
            for task in tasks_to_bill:
                if task.task_fee and task.task_fee > 0:
                    line_items_to_create.append({
                        'description': task.description,
                        'quantity': task.quantity or 1,
                        'unit_price': task.task_fee,
                        'tasks_to_link': [task]
                    })
        else:
            raise ValueError(f"Unknown billing type: {project.billing_type}")
        
        # Step 3: Check if any valid line items were generated.
        if not line_items_to_create:
            flash('No tasks with billable hours or fees were found.', 'info')
            return redirect(url_for('project_detail', project_id=project.id))

        # Step 4: Atomically get the next invoice number.
        sequence = InvoiceSequence.query.first()
        if not sequence:
            sequence = InvoiceSequence(next_invoice_num=1)
            db.session.add(sequence)
        
        invoice_num = sequence.next_invoice_num
        sequence.next_invoice_num += 1
        invoice_number_str = f'INV-{invoice_num:04d}'

        # Step 5: Create the invoice and line items.
        new_invoice = Invoice(
            invoice_number=invoice_number_str,
            project_id=project.id,
            user_id=current_user.id
        )
        db.session.add(new_invoice)

        for item_data in line_items_to_create:
            line_item = LineItem(
                description=item_data['description'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                invoice=new_invoice
            )
            db.session.add(line_item)
            db.session.flush() # Flush to get the line_item's ID
            # Mark all associated tasks as billed and link them.
            for task in item_data['tasks_to_link']:
                task.has_been_billed = True
                task.line_item_id = line_item.id
        
        # Step 6: Commit the transaction.
        db.session.commit()
        flash(f'Successfully generated Invoice {new_invoice.invoice_number}!', 'success')
        return redirect(url_for('invoice_detail', invoice_id=new_invoice.id))

    except Exception as e:
        db.session.rollback()
        # Use Flask's logger for better production debugging.
        app.logger.error(f"Error generating invoice for project {project.id}: {e}", exc_info=True)
        flash('An unexpected error occurred while generating the invoice. Please try again.', 'danger')
        return redirect(url_for('project_detail', project_id=project.id))