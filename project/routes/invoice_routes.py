from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from datetime import datetime
from weasyprint import HTML
from ..extensions import db
from ..models import Invoice, Project, LineItem, InvoiceSequence, Task

invoice_bp = Blueprint('invoices', __name__)

@invoice_bp.route('/invoices')
@login_required
def invoices():
    all_invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.issue_date.desc()).all()
    all_projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.title).all()
    return render_template('invoices.html', invoices=all_invoices, projects=all_projects)

@invoice_bp.route('/create-invoice', methods=['POST'])
@login_required
def create_invoice():
    project_id = request.form.get('project_id')
    if not project_id:
        flash('You must select a project.', 'danger')
        return redirect(url_for('invoices.invoices'))

    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()

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
    return redirect(url_for('invoices.invoice_detail', invoice_id=new_invoice.id))

@invoice_bp.route('/invoice/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    return render_template('invoice_detail.html', invoice=invoice)

@invoice_bp.route('/invoice/<int:invoice_id>/add-item', methods=['POST'])
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
        
    return redirect(url_for('invoices.invoice_detail', invoice_id=invoice.id))

@invoice_bp.route('/invoice/update-status/<int:invoice_id>', methods=['POST'])
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
    return redirect(url_for('invoices.invoices'))

@invoice_bp.route('/invoice/<int:invoice_id>/download-pdf')
@login_required
def download_pdf(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    rendered_html = render_template('invoice_pdf.html', invoice=invoice)
    pdf = HTML(string=rendered_html).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Invoice-{invoice.invoice_number}.pdf'
    return response

@invoice_bp.route('/project/<int:project_id>/generate-invoice', methods=['POST'])
@login_required
def generate_invoice(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()

    try:
        tasks_to_bill = Task.query.filter_by(
            project_id=project.id,
            is_completed=True,
            is_billable=True,
            has_been_billed=False
        ).all()

        if not tasks_to_bill:
            flash('No completed, unbilled tasks are available to invoice.', 'warning')
            return redirect(url_for('projects.project_detail', project_id=project.id))

        line_items_to_create = []
        if project.billing_type == 'Flat Fee':
            tasks_summary = '; '.join([task.description for task in tasks_to_bill])
            if len(tasks_summary) > 195:
                tasks_summary = tasks_summary[:195] + '...'
            
            line_items_to_create.append({
                'description': f'Project: {project.title} - {tasks_summary}',
                'quantity': 1,
                'unit_price': project.flat_fee_amount or 0.0,
                'tasks_to_link': tasks_to_bill
            })

        elif project.billing_type == 'Hourly':
            for task in tasks_to_bill:
                if task.total_hours_logged > 0:
                    rate = task.override_rate or project.hourly_rate or 0.0
                    line_items_to_create.append({
                        'description': task.description,
                        'quantity': task.total_hours_logged,
                        'unit_price': rate,
                        'tasks_to_link': [task]
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
        
        if not line_items_to_create:
            flash('No tasks with billable hours or fees were found.', 'info')
            return redirect(url_for('projects.project_detail', project_id=project.id))

        sequence = InvoiceSequence.query.first()
        if not sequence:
            sequence = InvoiceSequence(next_invoice_num=1)
            db.session.add(sequence)
        
        invoice_num = sequence.next_invoice_num
        sequence.next_invoice_num += 1
        invoice_number_str = f'INV-{invoice_num:04d}'

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
            db.session.flush()
            for task in item_data['tasks_to_link']:
                task.has_been_billed = True
                task.line_item_id = line_item.id
        
        db.session.commit()
        flash(f'Successfully generated Invoice {new_invoice.invoice_number}!', 'success')
        return redirect(url_for('invoices.invoice_detail', invoice_id=new_invoice.id))

    except Exception as e:
        db.session.rollback()
        flash('An unexpected error occurred while generating the invoice. Please try again.', 'danger')
        return redirect(url_for('projects.project_detail', project_id=project.id))