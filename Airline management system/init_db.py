from app import app
from models import db, Flight
from datetime import datetime, timedelta

with app.app_context():
    db.create_all()

    # sample flights (only if empty)
    if Flight.query.count() == 0:
        now = datetime.utcnow()
        f1 = Flight(code='AA101', origin='Dhaka', destination='Chittagong', depart=now + timedelta(days=1, hours=3), arrive=now + timedelta(days=1, hours=4), capacity=10)
        f2 = Flight(code='BB202', origin='Dhaka', destination='Sylhet', depart=now + timedelta(days=2, hours=5), arrive=now + timedelta(days=2, hours=6), capacity=8)
        db.session.add_all([f1, f2])
        db.session.commit()
        print('Sample flights added.')
    else:
        print('Flights already present.')
