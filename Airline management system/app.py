from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from config import Config
from models import db, User, Flight, Passenger, Booking, Payment, Cancellation
from forms import LoginForm
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import bcrypt
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home page
@app.route('/')
def index():
    flights = Flight.query.order_by(Flight.depart).all()
    return render_template('index.html', flights=flights)

# Simple login/logout
@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.checkpw(form.password.data.encode('utf-8'), user.password_hash.encode('utf-8')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Dashboard (admin)
@app.route('/dashboard')
@login_required
def dashboard():
    flights = Flight.query.order_by(Flight.depart).all()
    total_bookings = Booking.query.count()
    total_revenue = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
    return render_template('dashboard.html', flights=flights, total_bookings=total_bookings, total_revenue=total_revenue)

# Flight listing page
@app.route('/flights')
def flights():
    flights = Flight.query.order_by(Flight.depart).all()
    return render_template('flights.html', flights=flights)

# Book page (form)
@app.route('/book/<int:flight_id>')
def book_page(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    return render_template('book.html', flight=flight)

# BOOK API (transaction-safe, seat capacity check)
@app.route('/api/book', methods=['POST'])
def api_book():
    data = request.get_json()
    flight_id = data.get('flight_id')
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    seat_preference = data.get('seat_no')  # optional

    if not flight_id or not name:
        return jsonify({'error':'missing fields'}), 400

    try:
        # use session transaction
        with db.session.begin():
            # lock flight row
            stmt = select(Flight).where(Flight.id == flight_id).with_for_update()
            flight = db.session.execute(stmt).scalar_one_or_none()
            if not flight:
                return jsonify({'error':'flight not found'}), 404

            # count current confirmed bookings
            current = db.session.query(func.count(Booking.id)).filter_by(flight_id=flight_id, status='CONFIRMED').scalar()
            if current >= flight.capacity:
                return jsonify({'error':'no seats available'}), 409

            # create passenger
            passenger = Passenger(name=name, email=email, phone=phone)
            db.session.add(passenger)
            db.session.flush()  # gets passenger.id

            # determine seat_no: simple auto increment (1..capacity) avoiding occupied seats
            occupied = db.session.query(Booking.seat_no).filter_by(flight_id=flight_id, status='CONFIRMED').all()
            occupied_set = set([r[0] for r in occupied if r[0] is not None])

            # if user specified seat and it's free, take it
            seat_no = None
            if seat_preference:
                try:
                    sp = int(seat_preference)
                    if 1 <= sp <= flight.capacity and sp not in occupied_set:
                        seat_no = sp
                except:
                    seat_no = None

            # otherwise assign lowest free seat
            if seat_no is None:
                for s in range(1, flight.capacity + 1):
                    if s not in occupied_set:
                        seat_no = s
                        break

            booking = Booking(flight_id=flight_id, passenger_id=passenger.id, seat_no=seat_no)
            db.session.add(booking)
            db.session.flush()

            # create a dummy payment record (in real app integrate payment gateway)
            payment = Payment(booking_id=booking.id, amount=100.0, method='CASH', status='PAID', tx_ref=None)
            db.session.add(payment)

        # end transaction
        return jsonify({'status':'ok', 'booking_id': booking.id, 'seat_no': booking.seat_no}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error':'database error', 'detail': str(e)}), 500

# Cancel booking
@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    data = request.get_json()
    booking_id = data.get('booking_id')
    reason = data.get('reason', 'No reason provided')

    if not booking_id:
        return jsonify({'error':'missing booking_id'}), 400

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'error':'booking not found'}), 404
    if booking.status == 'CANCELLED':
        return jsonify({'error':'already cancelled'}), 400

    try:
        with db.session.begin():
            booking.status = 'CANCELLED'
            # create cancellation record and refund (simple 50% refund logic)
            refund = 50.0
            cancel = Cancellation(booking_id=booking.id, reason=reason, refund_amount=refund)
            db.session.add(cancel)
            # update payment
            payment = Payment.query.filter_by(booking_id=booking.id).first()
            if payment:
                payment.status = 'REFUNDED'
            # in real world trigger payment gateway refund
        return jsonify({'status':'ok', 'refund': refund}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error':'db error', 'detail': str(e)}), 500

# Simple report route
@app.route('/report')
@login_required
def report():
    # bookings per flight and revenue
    flights = Flight.query.all()
    report_data = []
    for f in flights:
        bookings = Booking.query.filter_by(flight_id=f.id, status='CONFIRMED').count()
        revenue = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).join(Booking, Booking.id==Payment.booking_id).filter(Booking.flight_id==f.id).scalar()
        report_data.append({'flight': f, 'bookings': bookings, 'revenue': revenue})
    return render_template('report.html', report_data=report_data)

# helper to create admin user (not production safe)
@app.cli.command('create-admin')
def create_admin():
    username = input('Admin username: ')
    pwd = input('Password: ')
    hashed = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(username=username, password_hash=hashed, is_admin=True)
    db.session.add(user)
    db.session.commit()
    print('Admin created.')

if __name__ == '__main__':
    app.run(debug=True)
