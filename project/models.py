# project/models.py

from .extensions import db
from flask_login import UserMixin
from datetime import date

# -----------------------
# Database Models (v4)
# -----------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

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
    notes = db.Column(db.Text, nullable=True)
    billing_type = db.Column(db.String(50), nullable=False, default='Hourly') # Options: Hourly, Flat Fee, Per Task
    hourly_rate = db.Column(db.Float, nullable=True)
    flat_fee_amount = db.Column(db.Float, nullable=True)


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

    # For Hourly Billing
    override_rate = db.Column(db.Float, nullable=True)

    # For Per-Task Billing
    task_fee = db.Column(db.Float, nullable=True)
    quantity = db.Column(db.Integer, nullable=True, default=1)

    # For Invoice Generation
    is_billable = db.Column(db.Boolean, default=True, nullable=False)
    has_been_billed = db.Column(db.Boolean, default=False, nullable=False)

    # Relationship to Time Entries
    time_entries = db.relationship('TimeEntry', backref='task', lazy=True, cascade="all, delete-orphan")
    line_item_id = db.Column(db.Integer, db.ForeignKey('line_item.id'), nullable=True)

    quantity_is_na = db.Column(db.Boolean, default=False, nullable=False)

    # NEW HELPER PROPERTY
    @property
    def total_hours_logged(self):
        return sum(entry.hours_worked for entry in self.time_entries)
    
class TimeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hours_worked = db.Column(db.Float, nullable=False)
    entry_date = db.Column(db.Date, nullable=False, default=date.today)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)

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

    # Establishes a one-to-one link from a LineItem back to a Task
    task = db.relationship('Task', backref='line_item', uselist=False)

    @property
    def amount(self):
        return self.quantity * self.unit_price
    
class InvoiceSequence(db.Model):
    """
    A simple table to store the next available invoice number to prevent race conditions
    and ensure sequential numbering. It should only ever contain one row.
    """
    id = db.Column(db.Integer, primary_key=True)
    next_invoice_num = db.Column(db.Integer, nullable=False, default=1)