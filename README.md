# Freelancer Manager SaaS

A lightweight, powerful web application designed to help freelancers and small service-based businesses manage their projects, track tasks, and eventually, generate invoices seamlessly. The goal is to provide a simple, intuitive tool that reduces administrative overhead and lets freelancers focus on their client work.

This project is being built iteratively using Python (Flask) for the backend and standard web technologies for the frontend.

## ✨ Current Features

As of the latest version, the application supports the following core functionalities:

  * **Project Management:** Create and view projects, each with a title and description.
  * **Task Management:** Break down projects into smaller, manageable tasks.
  * **Client Management:** Store and manage a directory of clients, linking them to their respective projects.
  * **Project Deadlines:** Assign and display a due date for each project to help with time management.
  * **Flexible Billing Models:** Choose a billing method for each project:
      * **Hourly:** Set an hourly rate.
      * **Fixed Fee:** Set a single, fixed price for the entire project.
      * **Per-Item:** (UI in place, logic to come).
  * **Database Migrations:** Uses `Flask-Migrate` (Alembic) to safely manage changes to the database schema.

-----

## 🛠️ Tech Stack

  * **Backend:** Python with the Flask web framework.
  * **Database:** SQLite for development, using SQLAlchemy as the ORM.
  * **Frontend:** HTML5, CSS3, and vanilla JavaScript.
  * **Styling:** Bootstrap 5 for a clean, responsive layout.
  * **Migrations:** Flask-Migrate to handle database schema evolution.

-----

## 🚀 Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

  * Python 3.x installed on your system.
  * `git` for version control.

### Installation & Setup

1.  **Clone the repository:**

    ```sh
    git clone https://github.com/basselfads23/freelancer-manager.git
    cd freelancer-manager
    ```

2.  **Create and activate a virtual environment:**

      * On Windows:
        ```sh
        py -m venv .venv
        .venv\Scripts\activate
        ```
      * On macOS/Linux:
        ```sh
        python3 -m venv .venv
        source .venv/bin/activate
        ```

3.  **Install the required packages:**

    ```sh
    pip install -r requirements.txt
    ```

4.  **Initialize and upgrade the database:**

      * If you're setting up for the first time or the database file (`freelancer_manager.db`) doesn't exist, run:
        ```sh
        flask db upgrade
        ```

5.  **Run the application:**

    ```sh
    flask run
    ```

    The application will be available at `http://127.0.0.1:5000`.

-----

## 📈 Project Changelog & History

This section documents the major development milestones since the project's inception.

  * **Commit 1: Initial Project Setup**

      * Initialized the project directory and Git repository.
      * Set up a Python virtual environment to manage dependencies.
      * Installed core packages: `Flask`, `Flask-SQLAlchemy`, and `Flask-Migrate`.
      * Established the basic project structure with `app.py`, `templates/`, and `static/` directories.

  * **Commit 2: Core Feature Implementation**

      * **Feature:** Implemented the foundational MVP (Minimum Viable Product) features.
      * **Details:**
          * Created the database models for `Project`, `Task`, and `Client`.
          * Built the user interface and backend routes to allow users to create, view, and manage projects and their associated tasks.
          * Added a dedicated page for client management.
          * Introduced a `deadline` feature for projects to track due dates.
          * Added support for flexible billing models (`hourly`, `fixed`, `item`) at the project level, making the app more versatile for different types of freelancers.
      * **Technical:** Successfully ran database migrations to add all new columns and tables without data loss. Fixed several bugs related to database migrations and template syntax.
