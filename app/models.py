# app/models.py
from app import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), nullable=False)  # Admin | Faculty | Student
    reservations = db.relationship('Reservation', back_populates='user', lazy='dynamic')


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

    id            = db.Column(db.Integer, primary_key=True)
    from_location = db.Column(db.String(120), nullable=False)
    to_location   = db.Column(db.String(120), nullable=False)
    distance      = db.Column(db.Integer, default=0)
    accessible    = db.Column(db.Boolean, default=True)
    kind          = db.Column(db.String(30), default="walk") # walk, stairs, elevator, ramp
    __table_args__ = (db.UniqueConstraint('from_location', 'to_location', 'kind'),)



class BookingRule(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    role      = db.Column(db.String(20), nullable=False, unique=True) # CHANGED from name
    max_hours = db.Column(db.Integer, default=2)


class Reservation(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    room_id     = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    start_time  = db.Column(db.DateTime, nullable=False)
    end_time    = db.Column(db.DateTime, nullable=False)
    status      = db.Column(db.String(20), default='Confirmed', nullable=False)

    user = db.relationship("User", back_populates="reservations")
    room = db.relationship("Room", back_populates="reservations")
    
    def overlaps(self, other_start, other_end):
        return max(self.start_time, other_start) < min(self.end_time, other_end)