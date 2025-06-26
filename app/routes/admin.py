# app/routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..models import Building, Room, User, BookingRule, Reservation
from ..models import Building, Room, User, BookingRule
from werkzeug.security import generate_password_hash
from sqlalchemy import func, desc

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required():
    # This check happens before every request to the blueprint
    if not current_user.is_authenticated or current_user.role != 'Admin':
        # Abort is better than redirect here as it stops execution
        # and can be caught by a proper error handler if needed.
        from flask import abort
        abort(403) # Forbidden

@bp.before_request
@login_required
def before_request_hook():
    admin_required()

@bp.route('/panel')
def panel():
    buildings = Building.query.order_by(Building.name).all()
    users = User.query.order_by(User.role, User.name).all()
    rules = BookingRule.query.order_by(BookingRule.role).all()
    return render_template('admin/admin_panel.html', buildings=buildings, users=users, rules=rules)

@bp.route('/reports')
def reports():
    """Show facility utilization reports."""
    # Query to count bookings per room
    bookings_per_room = db.session.query(
        Room.name,
        Building.name.label('building_name'),
        func.count(Reservation.id).label('booking_count')
    ).join(Reservation, Reservation.room_id == Room.id)\
     .join(Building, Room.building_id == Building.id)\
     .group_by(Room.id)\
     .order_by(desc('booking_count'))\
     .all()

    return render_template('admin/reports.html', bookings_per_room=bookings_per_room)
# CRUD for buildings
@bp.route('/buildings/add', methods=['POST'])
def add_building():
    name = request.form.get('name')
    if name and not Building.query.filter_by(name=name).first():
        building = Building(name=name)
        db.session.add(building)
        db.session.commit()
        flash(f'Building "{name}" added.', 'success')
    else:
        flash(f'Building name "{name}" is invalid or already exists.', 'danger')
    return redirect(url_for('admin.panel'))

# CRUD for rooms
@bp.route('/rooms/add', methods=['POST'])
def add_room():
    try:
        room = Room(
            building_id=int(request.form.get('building_id')),
            name=request.form.get('name'),
            type=request.form.get('type'),
            capacity=int(request.form.get('capacity'))
        )
        db.session.add(room)
        db.session.commit()
        flash(f'Room "{room.name}" added successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding room: {e}', 'danger')
    return redirect(url_for('admin.panel'))

# CRUD for users
@bp.route('/users/add', methods=['POST'])
def add_user():
    email = request.form.get('email')
    if email and not User.query.filter_by(email=email).first():
        user = User(
            name=request.form.get('name'),
            email=email,
            password_hash=generate_password_hash(request.form.get('password')),
            role=request.form.get('role')
        )
        db.session.add(user)
        db.session.commit()
        flash(f'User "{user.name}" added.', 'success')
    else:
        flash(f'Email "{email}" is invalid or already registered.', 'danger')
    return redirect(url_for('admin.panel'))

# CRUD for booking rules
@bp.route('/rules/update', methods=['POST'])
def update_rule():
    try:
        role = request.form.get('role')
        max_hours = int(request.form.get('max_hours'))

        rule = BookingRule.query.filter_by(role=role).first()
        if rule:
            rule.max_hours = max_hours
            flash(f'Rule for {role} updated to {max_hours} hours.', 'success')
        else:
            rule = BookingRule(role=role, max_hours=max_hours)
            db.session.add(rule)
            flash(f'Rule for {role} created: max {max_hours} hours.', 'success')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating rule: {e}', 'danger')
    return redirect(url_for('admin.panel'))