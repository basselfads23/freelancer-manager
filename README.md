# Freelancer Manager - v3.0.0

A simple web application built with **Flask** to help freelancers manage their **projects, clients, and now, individual tasks**.

---

## Features (v3.0)

This version introduces **Task Management**, building upon the **project and client features from v2.0**.

### Core Features

- All features from **v2.0**, including:
  - Project Management
  - Client Management

### **NEW: Detailed Project View**

- Each project on the dashboard now links to a **dedicated detail page** (e.g., `/project/1`).

### **NEW: Task Management**

- Add **new tasks** to a project on its detail page.
- View all tasks for a project in a **checklist format**.
- Mark tasks as **complete** or **incomplete** via a simple checkbox.
- Task status is **saved instantly** to the database.

### **NEW: Project Progress Tracking**

- The **main project dashboard** now displays a **progress indicator** for each project  
  _(e.g., “2 of 5 tasks complete”)_.
