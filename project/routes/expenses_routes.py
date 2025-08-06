# project/expenses.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date

# Import extensions and models
from ..extensions import db
from ..models import Expense, ExpenseCategory, Project

# Create a Blueprint for expenses
expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/expenses', methods=['GET', 'POST'])
@login_required
def list_expenses():
    """
    Handles viewing all expenses and adding a new expense.
    """
    if request.method == 'POST':
        # Logic for adding a new expense
        description = request.form.get('description')
        amount = request.form.get('amount')
        date_str = request.form.get('date')
        project_id = request.form.get('project_id')
        category_id = request.form.get('category_id')

        if description and amount and project_id and category_id:
            new_expense = Expense(
                description=description,
                amount=float(amount),
                date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                project_id=project_id,
                category_id=category_id,
                user_id=current_user.id
            )
            db.session.add(new_expense)
            db.session.commit()
            flash('Expense has been added successfully.', 'success')
        else:
            flash('Please fill out all required fields.', 'danger')
        
        return redirect(url_for('expenses.list_expenses'))

    # Logic for viewing the page (GET request)
    # We will pre-populate categories if they don't exist
    if ExpenseCategory.query.count() == 0:
        categories = ['Software', 'Hardware', 'Marketing', 'Travel', 'Office Supplies', 'Other']
        for cat_name in categories:
            db.session.add(ExpenseCategory(name=cat_name))
        db.session.commit()

    # Fetch all data needed for the template
    all_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    all_projects = Project.query.filter_by(user_id=current_user.id).all()
    all_categories = ExpenseCategory.query.all()

    return render_template('expenses.html', 
                           expenses=all_expenses, 
                           projects=all_projects, 
                           categories=all_categories,
                           date=date)

@expenses_bp.route('/expense/<int:expense_id>/delete', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """ Handles the deletion of a single expense. """
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    flash('Expense has been deleted.', 'success')
    return redirect(url_for('expenses.list_expenses'))