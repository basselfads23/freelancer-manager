from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from ..extensions import db
from ..models import Project, Client, Task, TimeEntry

project_bp = Blueprint('projects', __name__)

@project_bp.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        client_id = request.form.get('client_id')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None
        
        billing_type = request.form.get('billing_type')
        hourly_rate = request.form.get('hourly_rate')
        flat_fee_amount = request.form.get('flat_fee_amount')

        new_project = Project(
            title=title,
            description=description,
            deadline=deadline,
            client_id=client_id,
            user_id=current_user.id,
            billing_type=billing_type
        )
        
        if billing_type == 'Hourly':
            new_project.hourly_rate = float(hourly_rate) if hourly_rate else 0.0
        elif billing_type == 'Flat Fee':
            new_project.flat_fee_amount = float(flat_fee_amount) if flat_fee_amount else 0.0

        db.session.add(new_project)
        db.session.commit()
        flash(f'Project "{title}" created successfully.', 'success')
        return redirect(url_for('projects.project_detail', project_id=new_project.id))

    new_client_id = request.args.get('new_client_id', type=int)
    all_projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.deadline.asc()).all()
    all_clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()

    return render_template('projects.html', projects=all_projects, clients=all_clients, new_client_id=new_client_id)

@project_bp.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    return render_template('project_detail.html', project=project, date=date)

@project_bp.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    project_to_delete = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    db.session.delete(project_to_delete)
    db.session.commit()
    return redirect(url_for('projects.projects'))

@project_bp.route('/project/<int:project_id>/update-details', methods=['POST'])
@login_required
def update_project_details(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    
    data = request.get_json()
    new_title = data.get('project_title')

    if not new_title:
        return {'success': False, 'message': 'Title cannot be empty.'}, 400

    project.title = new_title
    db.session.commit()
    
    return {'success': True, 'new_title': project.title}

@project_bp.route('/add_task/<int:project_id>', methods=['POST'])
@login_required
def add_task(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    task_description = request.form.get('task_description')
    
    if not task_description:
        flash('Task description cannot be empty.', 'warning')
        return redirect(url_for('projects.project_detail', project_id=project.id))

    new_task = Task(
        description=task_description,
        project_id=project.id,
        user_id=current_user.id
    )

    if project.billing_type == 'Hourly':
        override_rate = request.form.get('override_rate')
        if override_rate:
            new_task.override_rate = float(override_rate)

    elif project.billing_type == 'Per Task':
        task_fee = request.form.get('task_fee')
        quantity = request.form.get('quantity', 1)
        
        if task_fee:
            new_task.task_fee = float(task_fee)
        new_task.quantity = int(quantity)
        new_task.quantity_is_na = 'quantity_is_na' in request.form

    db.session.add(new_task)
    db.session.commit()
    flash('New task added!', 'success')
        
    return redirect(url_for('projects.project_detail', project_id=project.id))

@project_bp.route('/toggle_task/<int:task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    task.is_completed = not task.is_completed
    db.session.commit()
    return {'success': True, 'is_completed': task.is_completed}

@project_bp.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    flash('Task has been deleted.', 'success')
    return redirect(url_for('projects.project_detail', project_id=project_id))

@project_bp.route('/time-entry/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_time_entry(entry_id):
    entry = TimeEntry.query.get_or_404(entry_id)
    
    if entry.task.user_id != current_user.id:
        flash('You are not authorized to delete this entry.', 'danger')
        return redirect(url_for('projects.projects'))

    project_id = entry.task.project_id
    db.session.delete(entry)
    db.session.commit()
    flash('Time entry has been deleted.', 'success')
    return redirect(url_for('projects.project_detail', project_id=project_id))

@project_bp.route('/task/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    task.description = request.form.get('description')

    if task.project.billing_type == 'Hourly':
        override_rate = request.form.get('override_rate')
        task.override_rate = float(override_rate) if override_rate else None

    elif task.project.billing_type == 'Per Task':
        task.task_fee = float(request.form.get('task_fee'))
        task.quantity = int(request.form.get('quantity'))
        task.quantity_is_na = 'quantity_is_na' in request.form

    db.session.commit()
    flash(f'Task "{task.description}" has been updated.', 'success')
    return redirect(url_for('projects.project_detail', project_id=task.project_id))

@project_bp.route('/task/<int:task_id>/log-time', methods=['POST'])
@login_required
def log_time(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    if task.project.billing_type != 'Hourly':
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

    return {
        'success': True,
        'entry': {
            'id': new_entry.id,
            'hours': new_entry.hours_worked,
            'date': new_entry.entry_date.strftime('%Y-%m-%d')
        },
        'total_hours': task.total_hours_logged
    }

@project_bp.route('/task/<int:task_id>/quick-log', methods=['POST'])
@login_required
def quick_log_time(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    if task.project.billing_type != 'Hourly':
        return {'success': False, 'message': 'Time can only be logged for hourly projects.'}

    new_entry = TimeEntry(hours_worked=0.25, task_id=task.id)
    db.session.add(new_entry)
    db.session.commit()
    
    return {'success': True, 'total_hours': task.total_hours_logged}

@project_bp.route('/task/<int:task_id>/update-billing', methods=['POST'])
@login_required
def update_task_billing(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    if task.project.billing_type != 'Per Task':
        flash('Task billing can only be updated for "Per Task" projects.', 'danger')
        return redirect(url_for('projects.project_detail', project_id=task.project_id))

    task_fee = request.form.get('task_fee')
    quantity = request.form.get('quantity')
    
    if task_fee:
        task.task_fee = float(task_fee)
    if quantity:
        task.quantity = int(quantity)

    db.session.commit()
    flash(f'Billing details for task "{task.description}" have been updated.', 'success')
    return redirect(url_for('projects.project_detail', project_id=task.project_id))