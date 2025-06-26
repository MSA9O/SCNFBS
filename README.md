# SCNFBS Updated Implementation

This implementation addresses the following:

1.  **Role‑Based Access Control** – Administrator, Faculty, and Student roles enforced on both the server and UI.
2.  **Administrator Functionality** – Admin panel for managing buildings, rooms, users, and booking rules with CRUD.
3.  **Frontend UI** – Responsive Bootstrap 5 templates for login, dashboard, booking, and admin panel with calendar‑ready form controls.
4.  **Security & Authentication** – Password hashing with Werkzeug, session management with Flask‑Login, protected routes.
5.  **User Accounts** – Registration, profile login, and a `seed_data.py` script that pre‑populates default accounts.
6.  **Navigation Functionality** – A unified shortest-path algorithm (Dijkstra's) using data from JSON files loaded into a consistent database model.

## Quick Start

The `seed_data.py` script will automatically drop all existing tables and re-create the database schema before populating it with sample data.

```bash
# 1. Set up a virtual environment
python -m venv venv
venv\Scripts\activate on Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize and seed the database
#    This command creates the 'instance/scnfbs.db' file and populates it.
python seed_data.py

# 4. Run the application
python run.py