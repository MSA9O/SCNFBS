# app/routes/booking.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from .. import db
from ..models import Room, Reservation, BookingRule, Building
from ..utils.email import send_email

bp = Blueprint('booking', __name__)

def check_role_access(room_type, user_role):
    """Checks permissions based on the new, more granular rules."""
    if user_role == 'Student':
        return room_type == 'Study'
    if user_role == 'Faculty':
        return room_type != 'Study'
    return False

def get_allowed_duration(user_role):
    """Get the max booking duration in hours for a user's role."""
    rule = BookingRule.query.filter_by(role=user_role).first()
    return rule.max_hours if rule else 2

@bp.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if current_user.role == 'Admin':
        flash("Admins manage facilities from the admin panel.", "info")
        return redirect(url_for('main.dashboard'))

    rooms_query = Room.query.join(Building)
    
    if current_user.role == 'Student':
        rooms_query = rooms_query.filter(Room.type == 'Study')
    elif current_user.role == 'Faculty':
        rooms_query = rooms_query.filter(Room.type != 'Study')
    else:
        rooms_query = rooms_query.filter(False) 
        
    available_rooms = rooms_query.order_by(Building.name, Room.name).all()

    if request.method == 'POST':
        try:
            room_id = int(request.form.get('room_id'))
            start_time_str = request.form.get('start_time')
            if not start_time_str: 
                flash("Start time is required.", "danger")
                return redirect(url_for('booking.book'))
            start_time = datetime.fromisoformat(start_time_str)
            duration_hours = int(request.form.get('duration'))
            recurrence_type = request.form.get('recurrence_type')
            recurrence_count = int(request.form.get('recurrence_count', 1)) 
            room = Room.query.get_or_404(room_id)
        except (ValueError, TypeError) as e:
            flash(f"Invalid form data. Please check your inputs. Error: {e}", "danger")
            return redirect(url_for('booking.book'))

        if not check_role_access(room.type, current_user.role):
            flash(f'Your role ({current_user.role}) does not have permission to book this type of facility ({room.type}).', 'danger')
            return redirect(url_for('booking.book'))
        
        max_duration = get_allowed_duration(current_user.role)
        if duration_hours > max_duration:
            flash(f'Duration exceeds the maximum of {max_duration} hours for your role.', 'danger')
            return redirect(url_for('booking.book'))
            
        dates_to_book = []
        if recurrence_type == 'weekly':
            if recurrence_count < 1:
                flash("Number of repetitions for weekly booking must be at least 1.", "warning")
                return redirect(url_for('booking.book'))
            for i in range(recurrence_count):
                dates_to_book.append(start_time + timedelta(weeks=i))
        else: 
            dates_to_book.append(start_time)
            
        successful_bookings = []
        failed_dates = []

        for booking_date in dates_to_book:
            end_time = booking_date + timedelta(hours=duration_hours)
            
            with db.session.no_autoflush:
                overlapping_reservation = Reservation.query.filter(
                    Reservation.room_id == room.id,
                    Reservation.status == 'Confirmed', 
                    Reservation.end_time > booking_date,
                    Reservation.start_time < end_time
                ).first()

            if overlapping_reservation:
                failed_dates.append(booking_date.strftime('%Y-%m-%d %H:%M'))
                continue

            new_reservation = Reservation(
                user_id=current_user.id,
                room_id=room.id,
                start_time=booking_date,
                end_time=end_time
            )
            db.session.add(new_reservation)
            successful_bookings.append(new_reservation)

        if successful_bookings:
            try:
                db.session.commit()
                
                first_booking = successful_bookings[0]
                send_email(
                    to=current_user.email,
                    subject='Your SCNFBS Booking is Confirmed',
                    template='email/booking_confirmation.html',
                    user=current_user,
                    booking=first_booking 
                )
                if len(successful_bookings) > 1:
                     flash(f'Successfully created {len(successful_bookings)} booking(s) for {room.name} (starting {successful_bookings[0].start_time.strftime("%Y-%m-%d %H:%M")}). A confirmation email has been sent for the first booking.', 'success')
                else:
                    flash(f'Successfully created booking for {room.name} at {successful_bookings[0].start_time.strftime("%Y-%m-%d %H:%M")}. A confirmation email has been sent.', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred while saving your booking(s): {str(e)}", "danger")
                return redirect(url_for('booking.book'))
        
        if failed_dates:
            flash(f'Could not book on the following dates/times due to conflicts: {", ".join(failed_dates)}', 'warning')
        
        if not successful_bookings and not failed_dates and dates_to_book:
            flash('No bookings were made. Please check the facility availability.', 'info')
        elif not dates_to_book:
            flash('No dates were specified for booking. Please check your recurrence settings.', 'info')


        return redirect(url_for('main.dashboard'))

    return render_template('booking.html', rooms=available_rooms, max_duration=get_allowed_duration(current_user.role))