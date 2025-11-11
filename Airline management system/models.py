from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Flight(db.Model):
    __tablename__ = 'flights'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    origin = db.Column(db.String(80), nullable=False)
    destination = db.Column(db.String(80), nullable=False)
    depart = db.Column(db.DateTime, nullable=False)
    arrive = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

    bookings = db.relationship('Booking', back_populates='flight')

class Passenger(db.Model):
    __tablename__ = 'passengers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    passport = db.Column(db.String(50), nullable=True)

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'), nullable=False)
    passenger_id = db.Column(db.Integer, db.ForeignKey('passengers.id'), nullable=False)
    seat_no = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='CONFIRMED')  # CONFIRMED / CANCELLED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    flight = db.relationship('Flight', back_populates='bookings')
    passenger = db.relationship('Passenger')

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='PAID')  # PAID / REFUNDED / PENDING
    tx_ref = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Cancellation(db.Model):
    __tablename__ = 'cancellations'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    reason = db.Column(db.String(250), nullable=True)
    refund_amount = db.Column(db.Float, nullable=True)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
