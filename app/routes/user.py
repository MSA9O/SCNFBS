# app/routes/user.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import Reservation,db
from datetime import datetime
from ..utils.email import send_email 

bp = Blueprint('user', __name__, url_prefix='/user')

@bp.route('/my-bookings')
@login_required
def my_bookings():
    """Display the current user's past and upcoming bookings."""
    now = datetime.utcnow()

    # Query reservations and join with related Room and Building
    # to avoid extra database queries in the template.
    upcoming_bookings = current_user.reservations.filter(
        Reservation.end_time >= now,
        Reservation.status == 'Confirmed'
    ).order_by(Reservation.start_time.asc()).all()
    
    past_bookings = current_user.reservations.filter(
        db.or_(Reservation.end_time < now, Reservation.status != 'Confirmed')
    ).order_by(Reservation.start_time.desc()).all()
    
    return render_template(
        'user/my_bookings.html',
        upcoming_bookings=upcoming_bookings,
        past_bookings=past_bookings
    )
    
@bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    """Cancel an upcoming booking."""
    booking = Reservation.query.get_or_404(booking_id)

    # Security check: ensure the booking belongs to the current user
    if booking.user_id != current_user.id:
        from flask import abort
        abort(403) # Forbidden

    # Users can only cancel upcoming bookings
    if booking.start_time < datetime.utcnow():
        flash("Cannot cancel a booking that has already started or passed.", "warning")
        return redirect(url_for('user.my_bookings'))
    booking.status = 'Canceled'
    db.session.commit()
    
    send_email(
        to=current_user.email,
        subject='Your SCNFBS Booking Has Been Canceled',
        template='email/cancellation_notice.html',
        user=current_user,
        booking=booking
    )
    
    flash("Your booking has been successfully canceled.", "success")
    return redirect(url_for('user.my_bookings'))   