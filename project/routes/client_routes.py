from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Client

client_bp = Blueprint('clients', __name__)

@client_bp.route('/clients', methods=['GET', 'POST'])
@login_required
def clients():
    next_url = request.args.get('next')

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        post_next_url = request.form.get('next')

        new_client = Client(name=name, email=email, user_id=current_user.id)
        db.session.add(new_client)
        db.session.commit()

        if post_next_url == 'projects':
            return redirect(url_for('projects.projects', new_client_id=new_client.id))

        return redirect(url_for('clients.clients'))

    all_clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    return render_template('clients.html', clients=all_clients, next_url=next_url)

@client_bp.route('/delete_client/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    client_to_delete = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    
    if client_to_delete.projects:
        flash(f'Cannot delete {client_to_delete.name}. They still have active projects.', 'danger')
    else:
        db.session.delete(client_to_delete)
        db.session.commit()
        flash(f'Client {client_to_delete.name} has been deleted.', 'success')
        
    return redirect(url_for('clients.clients'))