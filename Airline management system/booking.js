async function makeBooking(flightId, name, email, phone, seat_no) {
  const res = await fetch('/api/book', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({flight_id: flightId, name: name, email: email, phone: phone, seat_no: seat_no})
  });
  const data = await res.json();
  return {ok: res.ok, status: res.status, data};
}

document.getElementById('bookForm').addEventListener('submit', async function(e){
  e.preventDefault();
  const flightId = document.getElementById('flight_id').value;
  const name = document.getElementById('name').value;
  const email = document.getElementById('email').value;
  const phone = document.getElementById('phone').value;
  const seat_no = document.getElementById('seat_no').value;

  const res = await makeBooking(flightId, name, email, phone, seat_no);
  const resultDiv = document.getElementById('result');
  if (!res.ok) {
    resultDiv.innerText = 'Error: ' + (res.data.error || res.status);
  } else {
    resultDiv.innerText = 'Booked! ID: ' + res.data.booking_id + ' Seat: ' + res.data.seat_no;
  }
});
