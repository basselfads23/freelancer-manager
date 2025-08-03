# Freelancer Manager - v2.0.0

A simple web application built with **Flask** to help freelancers manage their **projects and clients**.

---

## Features

This version includes the following features:

### Project Management
- **Create Projects**: Add projects with a title, description (notes), and a deadline.
- **Dashboard View**: View all projects on a central dashboard, sorted by deadline.
- **Status Indicators**: Color-coded status for each project (e.g., *"Due in X days"*, *"Overdue"*).
- **Delete Projects**: Remove projects with a confirmation prompt.

### Client Management
- **Client List**: Create and manage clients with their name and email.
- **Project Assignment**: Assign projects to specific clients using a dropdown menu.
- **Dashboard Integration**: View which client a project belongs to directly on the main dashboard.
- **Safe Deletion**: Clients cannot be deleted if they still have projects assigned.
