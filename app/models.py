# app/models.py
from app import db
from flask_login import UserMixin

# ───────────────────────────────
# Core user & RBAC
# ───────────────────────────────
class User(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), nullable=False)  # Admin | Faculty | Student
    reservations = db.relationship('Reservation', back_populates='user', lazy='dynamic')

# ───────────────────────────────
# Campus structure
# ───────────────────────────────
class Building(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    name  = db.Column(db.String(120), unique=True, nullable=False)
    rooms = db.relationship("Room", back_populates="building", cascade="all, delete")


class Room(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(120), nullable=False)
    type         = db.Column(db.String(30), default="Room")   # Room | Lab | Auditorium
    capacity     = db.Column(db.Integer, default=10)          # ADDED
    building_id  = db.Column(db.Integer, db.ForeignKey(Building.id), nullable=False)
    building     = db.relationship("Building", back_populates="rooms")
    reservations = db.relationship("Reservation", back_populates="room") # ADDED for overlap check


class MapPath(db.Model):
    """
    A single directed edge in the campus graph. Can be inter-building,
    intra-building, or room-to-building-exit.
    """
    id            = db.Column(db.Integer, primary_key=True)
    from_location = db.Column(db.String(120), nullable=False)
    to_location   = db.Column(db.String(120), nullable=False)
    distance      = db.Column(db.Integer, default=0)
    accessible    = db.Column(db.Boolean, default=True)
    kind          = db.Column(db.String(30), default="walk") # walk, stairs, elevator, ramp
    # Make sure we don't have duplicate paths
    __table_args__ = (db.UniqueConstraint('from_location', 'to_location', 'kind'),)


# ───────────────────────────────
# Booking System
# ───────────────────────────────
class BookingRule(db.Model):
    """Admin-configurable rules (e.g., max hours per day)."""
    id        = db.Column(db.Integer, primary_key=True)
    role      = db.Column(db.String(20), nullable=False, unique=True) # CHANGED from name
    max_hours = db.Column(db.Integer, default=2)


class Reservation(db.Model):
    """Actual bookings made by users."""
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    room_id     = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    start_time  = db.Column(db.DateTime, nullable=False)
    end_time    = db.Column(db.DateTime, nullable=False)
    status      = db.Column(db.String(20), default='Confirmed', nullable=False)

    user = db.relationship("User", back_populates="reservations")
    room = db.relationship("Room", back_populates="reservations")
    
    # ADDED method to check for time conflicts
    def overlaps(self, other_start, other_end):
        """Check if this reservation overlaps with a given time range."""
        # Two events overlap if they don't start after the other one ends.
        # (self.start < other.end) and (other.start < self.end)
        return max(self.start_time, other_start) < min(self.end_time, other_end)