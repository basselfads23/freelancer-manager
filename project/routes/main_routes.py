# project/main_routes.py

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from ..extensions import db
from ..models import Client, Project, Invoice, LineItem, Expense

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@login_required
def dashboard():
    total_revenue = db.session.query(func.sum(LineItem.unit_price * LineItem.quantity)).join(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'Paid'
    ).scalar() or 0.0

    outstanding_revenue = db.session.query(func.sum(LineItem.unit_price * LineItem.quantity)).join(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'Sent'
    ).scalar() or 0.0
    
    total_invoiced = db.session.query(func.sum(LineItem.unit_price * LineItem.quantity)).join(Invoice).filter(
        Invoice.user_id == current_user.id
    ).scalar() or 0.0

    revenue_by_client = db.session.query(
        Client.name,
        func.sum(LineItem.unit_price * LineItem.quantity)
    ).join(Project).join(Invoice).join(LineItem).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == 'Paid'
    ).group_by(Client.name).order_by(Client.name).all()

    total_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id
    ).scalar() or 0.0

    net_profit = total_revenue - total_expenses
    
    return render_template(
        'dashboard.html',
        total_revenue=total_revenue,
        outstanding_revenue=outstanding_revenue,
        total_invoiced=total_invoiced,
        revenue_by_client=revenue_by_client,
        total_expenses=total_expenses,
        net_profit=net_profit
    )

@main.route('/project/<int:project_id>/save-notes', methods=['POST'])
@login_required
def save_notes(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    
    notes_content = request.form.get('notes')
    project.notes = notes_content
    
    db.session.commit()
    
    flash('Project notes have been saved.', 'success')
    return redirect(url_for('projects.project_detail', project_id=project.id))