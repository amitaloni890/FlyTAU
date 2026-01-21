from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from utilise import Customer, RegisteredUser, Manager, Flight, Order, SessionService, DBService, Airplane, Route, Guest
from datetime import datetime, timedelta, date

app = Flask(__name__)
app.config.update(
    SESSION_TYPE="filesystem",
    SESSION_FILE_DIR="/home/amitaloni890/FlyTAU/flask_session_data",
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    SESSION_REFRESH_EACH_REQUEST=True,
    SESSION_COOKIE_SECURE=True
)
Session(app)

# ==================================================
# HOMEPAGE & NAVIGATION
# ==================================================
@app.route('/')
def homepage():
    """
        Acts as the main dashboard for the system.
        1. Detects the user role (Admin, User, or Guest) to show the correct interface.
        2. Filters the flight list based on user search inputs like date and destination.
        3. Displays the 'Popular Destinations' section with real-time dynamic pricing.
    """
    username = SessionService.get_username(session)
    role = SessionService.get_user_role(session)

    origin = request.values.get("origin", "").upper().strip()
    destination = request.values.get("destination", "").upper().strip()

    filters = {
        "departure_date": request.values.get('departure_date'),
        "origin": origin if origin else None,
        "destination": destination if destination else None,
        "status": request.values.get('status')
    }

    today = date.today().strftime('%Y-%m-%d')

    flights = Flight.search(filters=filters, for_manager=(role == "admin"))
    popular_destinations = Flight.get_popular_destinations()

    return render_template(
        'homepage.html',
        flights=flights,
        role=role,
        username=username,
        today=today,
        popular_destinations=popular_destinations
    )

@app.route('/flight/<flight_id>')
def flight_details(flight_id):
    """
    Displays detailed information about a specific flight.
    """
    flight = Flight.get_by_id(flight_id)
    if not flight:
        return "Flight not found", 404
    return render_template(
        'flight_details.html',
        flight=flight,
        role=SessionService.get_user_role(session),
        username=SessionService.get_username(session)
    )

# ==================================================
# AUTHENTICATION & REGISTRATION
# ==================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Authenticates a registered customers. Redirects to the next intended page
    after successful login (e.g., back to seat selection).
    """
    if request.method == 'POST':
        user = RegisteredUser.login(
            request.form.get('user_email').lower(),
            request.form.get('password')
        )
        if user:
            next_page = session.get('next')
            session.clear()
            session['User_email'] = user.email
            session['Username'] = f"{user.first_name} {user.last_name}"
            return redirect(next_page if next_page else '/')
        return render_template('login.html', message="Invalid credentials")
    return render_template('login.html')

@app.route('/login_manager', methods=['GET', 'POST'])
def login_manager():
    """
    Handles login for airline managers using their Employee ID.
    """
    if request.method == 'POST':
        manager = Manager.login(
            request.form.get('employee_ID'),
            request.form.get('password')
        )
        if manager:
            session.clear()
            session['Manager_ID'] = manager['Employee_ID']
            session['Manager_Name'] = manager['First_Name']
            return redirect('/')
        return render_template('login_manager.html', message="Invalid credentials")
    return render_template('login_manager.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
        Handles the creation of new member accounts.
        1. Ensures the user meets the minimum age requirement of 16.
        2. Manages multiple phone numbers during the sign-up process.
        3. Converts existing Guest records to 'Registered' status if the email matches.
    """

    max_birth_date = date(date.today().year - 16, date.today().month, date.today().day).isoformat()

    if request.method == 'GET':
        session['temp_phones'] = ['']
        return render_template('register.html', max_birth_date=max_birth_date, phones=session['temp_phones'])

    if request.method == 'POST':
        if SessionService.handle_temp_phones(session, request.form):
            return render_template('register.html', max_birth_date=max_birth_date, phones=session['temp_phones'])

        data = {
            "email": request.form.get('user_email').lower(),
            "first_name": request.form.get('first_name'),
            "last_name": request.form.get('last_name'),
            "password": request.form.get('password'),
            "birth_date": request.form.get('birth_date'),
            "passport": request.form.get('passport_number'),
            "customer_type": "Registered"
        }
        phone_numbers = [p for p in session['temp_phones'] if p.strip()]

        if not Customer.is_adult(data["birth_date"]):
            return render_template('register.html', message="Min age is 16",
                                   max_birth_date=max_birth_date, phones=session['temp_phones'])

        RegisteredUser.migrate_guest_data(data["email"])

        if not RegisteredUser.register(data, phone_numbers):
            return render_template('register.html', message="User already exists",
                                   max_birth_date=max_birth_date, phones=session['temp_phones'])

        next_page = session.get('next')
        session.clear()
        session['User_email'] = data["email"]
        session['Username'] = f"{data['first_name']} {data['last_name']}"
        return redirect(next_page if next_page else '/')

@app.route('/logout')
def logout():
    """ Terminates the current session and redirects to the homepage. """
    session.clear()
    return redirect('/')


# ==================================================
# BOOKING PROCESS (GUEST & REGISTERED)
# ==================================================

@app.route('/order_flight/<flight_id>')
def order_flight(flight_id):
    """
    Starts the booking flow. Authenticated users proceed to seat selection;
    unauthenticated users are sent to login.
    """
    if 'User_email' in session:
        return redirect(f'/select_seats/{flight_id}')
    session['next'] = f'/select_seats/{flight_id}'
    return redirect('/login')

@app.route('/guest_login')
def guest_login():
    """ Allows users to book flights without an account as a Guest. """
    next_page = session.get('next')
    session.clear()
    session['guest'] = True
    session['next'] = next_page
    if next_page:
        return redirect(next_page.replace('/select_seats', '/guest_checkout'))
    return redirect('/')

@app.route('/guest_checkout/<flight_id>', methods=['GET', 'POST'])
def guest_checkout(flight_id):
    """
        Manages the checkout process for guest travelers.
        1. Validates that the flight exists and the user is in 'guest' mode.
        2. Handles dynamic phone number fields through temporary session storage.
        3. Verifies that the guest's email is not already linked to a registered account.
        4. Enforces the 16-year minimum age requirement for making a booking.
        5. Stores validated guest details in the session to proceed to seat selection.
    """
    if 'guest' not in session:
        return redirect('/')

    class_type = request.args.get('class_type', 'Economy')
    flight = Flight.get_by_id(flight_id, class_type)
    if not flight:
        return "Flight not found", 404

    max_birth_date = date(date.today().year - 16, date.today().month, date.today().day).isoformat()

    if request.method == 'GET':
        session['temp_phones'] = ['']
        return render_template('guest_checkout.html', flight=flight, flight_id=flight_id,
                               max_birth_date=max_birth_date, phones=session['temp_phones'])

    if SessionService.handle_temp_phones(session, request.form):
        return render_template('guest_checkout.html', flight=flight, flight_id=flight_id,
                               max_birth_date=max_birth_date, phones=session['temp_phones'])

    if request.method == 'POST':
        email = request.form.get('email').lower()

        # Check if email is already in the system as a registered user
        is_registered = DBService.run("SELECT 1 FROM RegisteredUser WHERE Email=?", (email,), fetchone=True)
        if is_registered:
            session['next'] = f'/select_seats/{flight_id}'
            return render_template('guest_checkout.html', flight=flight, flight_id=flight_id,
                                   message="This email is already registered. Please log in.",
                                   max_birth_date=max_birth_date, phones=session['temp_phones'])

        birth_date_str = request.form.get('birth_date')
        if not Customer.is_adult(birth_date_str):
            return render_template('guest_checkout.html', flight=flight, flight_id=flight_id,
                                   message="You must be at least 16 years old to book a flight",
                                   max_birth_date=max_birth_date, phones=session['temp_phones'])

        # Save guest info and proceed
        session['guest_info'] = {
            "first_name": request.form.get('first_name'),
            "last_name": request.form.get('last_name'),
            "email": email,
            "birth_date": birth_date_str,
            "phones": [p for p in session['temp_phones'] if p.strip()]
        }
        session['guest_email'] = email
        session.pop('temp_phones', None)

        return redirect(f'/select_seats/{flight_id}')

    return render_template('guest_checkout.html', flight=flight, flight_id=flight_id,
                           max_birth_date=max_birth_date, phones=session.get('temp_phones', ['']))

@app.route('/select_seats/<flight_id>', methods=['GET', 'POST'])
def select_seats(flight_id):
    """ Renders the seat selection map based on airplane availability. """
    selected_seats = request.args.getlist('selected_seats')
    class_type = selected_seats[0].split('-')[0] if selected_seats else 'Economy'
    flight = Flight.get_by_id(flight_id, class_type)
    if not flight:
        return "Flight not found", 404
    seats, availability = flight.get_seat_map()
    return render_template('select_seats.html', flight=flight, seats=seats, availability=availability)

@app.route('/confirm_seats/<flight_id>', methods=['POST'])
def confirm_seats(flight_id):
    """ Validates selected seats and calculates total price for the order. """
    selected_seats = request.form.getlist('selected_seats')
    if not selected_seats:
        return redirect(f'/select_seats/{flight_id}')
    class_type = selected_seats[0].split('-')[0]
    flight = Flight.get_by_id(flight_id, class_type)
    if not flight:
        return "Flight not found", 404

    total_price = flight.calculate_total_price(selected_seats)

    return render_template(
        'order_summary.html',
        flight=flight,
        selected_seats=selected_seats,
        total_price=total_price
    )

@app.route('/order_summary/<flight_id>', methods=['POST'])
def order_summary(flight_id):
    """ Displays the order review page before the transaction is finalized. """
    selected_seats = request.form.getlist('selected_seats')
    if not selected_seats:
        return redirect(f'/select_seats/{flight_id}')
    class_type = selected_seats[0].split('-')[0]
    flight = Flight.get_by_id(flight_id, class_type)
    if not flight:
        return "Flight not found", 404

    total_price = flight.calculate_total_price(selected_seats)

    return render_template(
        'order_summary.html',
        flight=flight,
        selected_seats=selected_seats,
        total_price=total_price
    )

@app.route('/confirm_order/<flight_id>', methods=['POST'])
def confirm_order(flight_id):
    """ Finalizes the booking by creating Orders and Tickets in the database. """
    flight = Flight.get_by_id(flight_id)
    selected_seats = request.form.getlist('selected_seats')

    if not flight or not selected_seats:
        return redirect(f'/order_summary/{flight_id}')

    total_price = flight.calculate_total_price(selected_seats)
    role = SessionService.get_user_role(session)

    if role == 'guest':
        guest_data = session.get('guest_info')
        customer_email = guest_data['email']
        customer_type = 'Guest'

        # Save guest if new using Guest class
        if not DBService.run("SELECT 1 FROM Guests WHERE Email=?", (customer_email,), fetchone=True):
            Guest(customer_email, guest_data['first_name'], guest_data['last_name'],
                  guest_data.get('phones', [])).save_to_db()

    else:
        customer_email = session.get('User_email')
        customer_type = 'Registered'

    order_id = Order.create_full_order(flight_id, customer_email, customer_type, total_price, selected_seats)

    return render_template('confirm_order.html', order_number=order_id, is_guest=(customer_type == 'Guest'))

# ==================================================
# ACCOUNT MANAGEMENT
# ==================================================
@app.route('/my_account')
def my_account():
    """ Displays user profile and booking history, split into active and past orders. """
    if not SessionService.get_user_role(session):
        return redirect('/login')
    username = SessionService.get_username(session)
    now = datetime.now()
    cancel_time_limit = now + timedelta(hours=36)
    selected_status = request.args.get('status', '')

    if session.get('is_guest_view'):
        raw_orders = Order.get_guest_orders(session.get('guest_order_id'), session.get('guest_email'))
        is_guest = True
    else:
        if 'User_email' not in session:
            return redirect('/login')
        raw_orders = Order.get_user_orders(session['User_email'])
        is_guest = False

    active_orders = []
    past_orders = []
    seen_order_ids = set()

    for o in raw_orders:
        if o['order_id'] in seen_order_ids:
            continue
        seen_order_ids.add(o['order_id'])

        seats_data = Order.get_seats_by_order(o['order_id'])
        o['seats'] = seats_data

        dep_time = o['departure_time']

        if dep_time and isinstance(dep_time, datetime) and dep_time > now and o['status'] == 'Active':
            o['display_status'] = 'Active'
            active_orders.append(o)
        else:
            if not selected_status or o['display_status'] == selected_status:
                past_orders.append(o)

    return render_template(
        'my_account.html',
        active_orders=active_orders,
        past_orders=past_orders,
        is_guest=is_guest,
        cancel_time_limit=cancel_time_limit,
        selected_status=selected_status,
        username=username
    )

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    """
    Processes order cancellation request according to the 36-hour policy.
    Applies a 5% cancellation fee if applicable.
    """
    email = None
    if not session.get('guest', False):
        email = session['User_email']

    orders = Order.get_user_orders(email) if email else Order.get_guest_orders(order_id, session.get('guest_email', 'guest@example.com'))
    order = next((o for o in orders if o['order_id'] == order_id), None)

    canceled = False
    new_price = None
    now = datetime.now()

    if order:
        dep_time = order['departure_time']
        if dep_time and isinstance(dep_time, datetime):
            limit = now + timedelta(hours=36)

            if dep_time > limit:
                new_price = round(float(order.get('total_price', 0)) * 0.05, 2)
                Order.update_order(order_id, status='Customer Cancellation', total_price=new_price)
                canceled = True

                DBService.run(
                    "UPDATE Flights SET Status = 'Active' WHERE Flight_ID = ? AND Status = 'Fully Booked'",
                    (order['flight_id'],)
                )
            orders = Order.get_user_orders(email) if email else Order.get_guest_orders(order_id, session.get('guest_email', 'guest@example.com'))

    active_orders = []
    past_orders = []
    current_time_str = now.strftime('%Y-%m-%d %H:%M')

    for o in orders:
        o['seats'] = Order.get_seats_by_order(o['order_id'])
        if o['status'] == 'Active' and o['departure_time'] >  current_time_str:
            o['display_status'] = 'Active'
            active_orders.append(o)
        else:
            past_orders.append(o)

    return render_template(
        'my_account.html',
        role=SessionService.get_user_role(session),
        username=SessionService.get_username(session),
        is_guest=session.get('guest', False),
        canceled=canceled,
        new_price=new_price,
        active_orders=active_orders,
        past_orders=past_orders,
        cancel_time_limit=datetime.now() + timedelta(hours=36)
    )

@app.route('/manage_booking', methods=['GET', 'POST'])
def manage_booking():
    """ Allows guests to find and view their orders using Order ID and email. """
    if request.method == 'POST':
        order_id = request.form['order_id']
        email = request.form['email'].lower()

        order = Order.get_guest_orders(order_id, email)
        if not order:
            return render_template('manage_booking.html', error="Order not found. Please check your details.")

        is_registered = DBService.run("SELECT 1 FROM RegisteredUser WHERE Email=?", (email,), fetchone=True)

        if is_registered:
            if session.get('User_email') != email:
                session['next'] = '/my_account'
                return render_template('login.html',
                                       message="Please log in to view your orders.",
                                       is_info=True)
            else:
                return redirect('/my_account')

        session['guest_order_id'] = order_id
        session['guest_email'] = email
        session['is_guest_view'] = True
        session['guest'] = True

        return redirect('/my_account')

    return render_template('manage_booking.html')

# ==================================================
# ADMINISTRATIVE TOOLS
# ==================================================
@app.route('/add_crew', methods=['GET', 'POST'])
def add_crew():
    """ Admin route to add a new flight crew member to the system. """
    if SessionService.get_user_role(session) != 'admin':
        return redirect('/login_manager')
    message = None
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        city = request.form.get('city')
        street = request.form.get('street')
        house_number = request.form.get('house_number')
        phone_number = request.form.get('phone_number')
        start_date = request.form.get('start_date')
        role = request.form.get('role')

        qualifications = 1 if request.form.get('qualifications') == '1' else 0

        success = Manager.add_flight_crew(
            employee_id, first_name, last_name, city, street,
            house_number, phone_number, start_date, role, qualifications
        )
        if success:
            message = "Crew member added successfully!"
        else:
            message = "Could not add crew member."
    return render_template('add_crew.html', message=message)


@app.route("/add_flight", methods=["GET", "POST"])
def add_flight():
    """
        Create new flights by managers.
        1. Select the flight route (where to start and where to land).
        2. Show only airplanes that are at the right airport and fit the flight time.
        3. Show only pilots and attendants who are available and ready to fly.
        4. Make sure there are enough crew members before saving the flight.
    """
    if SessionService.get_user_role(session) != 'admin':
        return redirect('/login_manager')
    airports = Flight.get_all_airports()
    today = datetime.now().strftime("%Y-%m-%dT%H:%M")
    step = request.form.get("step")

    if request.method == "GET":
        return render_template("add_flight.html", step=1, airports=airports, today=today)

    # STEP 1: Select Origin -> Fetch available Destinations
    if step == "1":
        origin = request.form.get("origin_airport")
        destinations = Flight.get_destinations_for_origin(origin)
        return render_template("add_flight.html", step=2, origin=origin, destinations=destinations, today=today)

    # STEP 2: Select Route & Time -> Fetch available Airplanes
    if step == "2":
        origin = request.form.get("origin_airport")
        destination = request.form.get("destination_airport")
        departure_time_str = request.form.get("departure_time")

        duration = Flight.get_route_duration(origin, destination)
        flight_type = Flight.determine_flight_type(duration)
        airplanes = Flight.get_available_airplanes(origin, DBService, flight_type, departure_time_str)

        return render_template("add_flight.html", step=3, origin=origin, destination=destination,
                               departure_time=departure_time_str, airplanes=airplanes, flight_type=flight_type)

    # STEP 3: Select Airplane -> Fetch available Crew (Pilots & Attendants)
    if step == "3":
        origin = request.form.get("origin_airport")
        destination = request.form.get("destination_airport")
        departure_time_str = request.form.get("departure_time")
        airplane_id = request.form.get("airplane_id")

        # Get airplane details and calculate flight metadata
        plane_info = DBService.run("SELECT Size FROM Airplanes WHERE Airplane_ID = ?", (airplane_id,), fetchone=True)
        duration = Flight.get_route_duration(origin, destination)
        flight_type = Flight.determine_flight_type(duration)
        arrival_time = datetime.fromisoformat(departure_time_str) + timedelta(minutes=duration)

        pilots, attendants = Flight.get_available_crew(DBService, origin, flight_type, departure_time_str)

        return render_template("add_flight.html", step=4, origin=origin, destination=destination,
                               departure_time=departure_time_str, airplane_id=airplane_id,
                               airplane_size=plane_info['Size'], pilots=pilots, attendants=attendants,
                               arrival_time=arrival_time.strftime('%Y-%m-%d %H:%M'),
                               duration=duration, flight_type=flight_type)

    # STEP 4: Select Crew & Prices -> Validation & Creation
    if step == "4":
        origin = request.form.get("origin_airport")
        destination = request.form.get("destination_airport")
        departure_time = request.form.get("departure_time")
        airplane_id = request.form.get("airplane_id")
        pilot_ids = request.form.getlist("pilot_ids")
        attendant_ids = request.form.getlist("attendant_ids")

        # Get plane size for safety validation
        plane_info = DBService.run("SELECT Size FROM Airplanes WHERE Airplane_ID = ?", (airplane_id,), fetchone=True)

        is_valid, error_message = Flight.validate_crew_requirements(
            plane_info['Size'], len(pilot_ids), len(attendant_ids)
        )

        if error_message:
            duration = Flight.get_route_duration(origin, destination)
            flight_type = Flight.determine_flight_type(duration)
            pilots, attendants = Flight.get_available_crew(DBService, origin, flight_type, departure_time)

            return render_template("add_flight.html", step=4, error_msg=error_message,
                                   origin=origin, destination=destination, departure_time=departure_time,
                                   airplane_id=airplane_id, airplane_size=plane_info['Size'],
                                   pilots=pilots, attendants=attendants, today=today)

        duration = Flight.get_route_duration(origin, destination)
        dep_dt = datetime.fromisoformat(departure_time.replace(' ', 'T'))
        arrival_time = (dep_dt + timedelta(minutes=duration)).strftime('%Y-%m-%d %H:%M')

        Flight.create_flight(origin, destination, departure_time, arrival_time, airplane_id, pilot_ids, attendant_ids, DBService, request.form.get("price_regular"),
        request.form.get("price_business"))

        return render_template("add_flight.html", step=1, airports=airports, today=today,
                               success_msg="Flight created successfully!")

@app.route('/cancel_flight/<flight_id>')
def cancel_flight(flight_id):
    """ Admin route to cancel an entire flight and its associated orders. """
    if SessionService.get_user_role(session) != 'admin':
        return redirect('/login_manager')
    DBService.run(
        "UPDATE Orders SET Total_Price = 0, Status = 'System Cancellation' WHERE Flight_IDFK = ?",
        (flight_id,)
    )
    DBService.run(
        "UPDATE Flights SET Status = 'Canceled' WHERE Flight_ID = ?",
        (flight_id,)
    )
    class_type = request.args.get('class_type', 'Economy')
    flight = Flight.get_by_id(flight_id, class_type)
    return render_template(
        'flight_details.html',
        flight=flight,
        role=SessionService.get_user_role(session),
        username=SessionService.get_username(session),
        canceled=True
    )

@app.route("/add_airplane", methods=["GET", "POST"])
def add_airplane():
    """
    A tool for managers to add new airplanes.
    1. Collects basic airplane info like ID, size, and manufacturer.
    2. Uses the Airplane utility to set up seating classes and save to the database.
    """
    if SessionService.get_user_role(session) != 'admin':
        return redirect('/login_manager')
    if request.method == "GET":
        return render_template("add_airplane.html", step=1)

    step = request.form.get("step")

    if step == "1":
        airplane_data = {
            "airplane_id": request.form.get("airplane_id"),
            "manufacturer": request.form.get("manufacturer"),
            "size": request.form.get("size"),
            "purchase_date": request.form.get("purchase_date")
        }
        return render_template("add_airplane.html", step=2, data=airplane_data)

    if step == "2":
        success = Airplane.create_full_airplane(request.form)

        message = "Airplane added successfully!" if success else "Could not save airplane details."
        return render_template("add_airplane.html", step=1, message=message)

@app.route('/add_route', methods=['GET', 'POST'])
def add_route():
    """A tool for managers to define new flight paths between airports."""
    if SessionService.get_user_role(session) != 'admin':
        return redirect('/login_manager')

    message = None
    success = False

    if request.method == 'POST':
        origin = request.form.get('origin').upper()
        destination = request.form.get('destination').upper()
        duration = request.form.get('duration')

        if origin == destination:
            message = "Origin and Destination cannot be the same."
            success = False
        else:
            success, message = Route.add_route(origin, destination, int(duration))

    return render_template('add_route.html', message=message, success=success)


@app.route("/reports")
def reports():
    """Shows the manager's dashboard with real-time business data."""
    if SessionService.get_user_role(session) != 'admin':
        return redirect('/login_manager')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    assets = Manager.build_manager_dashboard(start_date, end_date)

    return render_template("reports.html", assets=assets)