import sqlite3
import random
import string
from contextlib import contextmanager
from datetime import datetime, date


# ==================================================
# DB SERVICE
# ==================================================
class DBService:
    """
        This class handles the connection to our SQLite database.
        It saves us from writing the connection code every time we want to run a query.
    """

    @staticmethod
    def get_db():
        db_path = "/home/amitaloni890/FlyTAU/flytau.db"
        mydb = sqlite3.connect(db_path, check_same_thread=False)
        mydb.row_factory = sqlite3.Row
        mydb.isolation_level = None
        return mydb

    @staticmethod
    @contextmanager
    def db_cur():
        db = DBService.get_db()
        cursor = db.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
            db.close()

    @staticmethod
    def run(query, params=None, fetchone=False, fetchall=False):
        """
        Executes a SQL query.
        - Use 'fetchone' to get one result (like finding a specific user).
        - Use 'fetchall' to get a list (like all available flights).
        """
        with DBService.db_cur() as cursor:
            cursor.execute(query, params or [])
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            return None


# ==================================================
# SESSION & AUTHENTICATION SERVICE
# ==================================================
class SessionService:
    """
    Helps us manage who is currently logged in (Admin, User, or Guest).
    """
    @staticmethod
    def get_user_role(session):
        """ Returns the current user's role: 'admin', 'user', 'guest', or None. """
        if 'Manager_ID' in session:
            return 'admin'
        elif 'User_email' in session:
            return 'user'
        elif session.get('guest', False):
            return 'guest'
        return None

    @staticmethod
    def get_username(session):
        """ Returns the display name of the current user based on their role. """
        role = SessionService.get_user_role(session)
        if role == 'admin':
            return session.get('Manager_Name', '')
        if role == 'user':
            return session.get('Username', '')
        if role == 'guest':
            return 'Guest'
        return ''

    @staticmethod
    def handle_temp_phones(session, request_form):
        """
        Manages dynamic phone number fields in the session for the registration and checkout forms..
        """
        current_phones = request_form.getlist('phone_numbers')
        session['temp_phones'] = current_phones
        if 'add_phone_field' in request_form:
            session['temp_phones'].append('')
            return True  # Indicates a field was added
        return False

# ==================================================
# CUSTOMER MODELS (CUSTOMER, REGISTERED, GUEST)
# ==================================================
class Customer:
    """ Base class for all customers (Registered and Guests). """

    def __init__(self, email, first_name, last_name, phone_numbers, customer_type):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.customer_type = customer_type
        self.phone_numbers = phone_numbers

    def save_phone_numbers(self, table_name):
        """ Iterates through phone numbers and saves them to the specified table. """
        for phone in self.phone_numbers:
            DBService.run(
                f"INSERT INTO {table_name} (Email, Phone_number, Customer_type) VALUES (?, ?, ?)",
                (self.email, phone, self.customer_type),
            )

    @staticmethod
    def is_adult(birth_date_str, min_age=16):
        """ Validates that the person is at least 16 years old. """
        birth_date = date.fromisoformat(birth_date_str)
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age >= min_age


class RegisteredUser(Customer):
    """ Represents a customer who has registered an account in the system. """
    def __init__(self, email, first_name, last_name, password, birth_date, passport, registered_date, phone_numbers):
        super().__init__(email, first_name, last_name, phone_numbers, customer_type="Registered")
        self.password = password
        self.birth_date = birth_date
        self.passport = passport
        self.registered_date = registered_date

    @classmethod
    def register(cls, data, phone_numbers):
        if DBService.run("SELECT 1 FROM RegisteredUser WHERE Email=?", (data["email"],), fetchone=True):
            return None
        DBService.run("DELETE FROM Phone_Numbers WHERE Email = ?", (data["email"],))
        registered_date = datetime.now().date()
        DBService.run(
            """
            INSERT INTO RegisteredUser
            (Email, Customer_type, User_Passport, Password, First_Name, Last_Name, Birth_Date, Registered_Date)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                data["email"], "Registered", data["passport"], data["password"],
                data["first_name"], data["last_name"], data["birth_date"], registered_date
            ),
        )

        if phone_numbers:
            user_obj = cls(
                data["email"], data["first_name"], data["last_name"],
                data["password"], data["birth_date"], data["passport"],
                registered_date, phone_numbers
            )
            user_obj.save_phone_numbers("Phone_Numbers")

        return True

    @classmethod
    def login(cls, email, password):
        """ Validates email and password, returning a RegisteredUser object if valid. """
        row = DBService.run(
            "SELECT Email, Password, First_Name, Last_Name, Birth_Date, User_Passport, Registered_Date FROM RegisteredUser WHERE Email=?",
            (email,), fetchone=True
        )
        if not row or row['Password'] != password:
            return None
        phones = [p['Phone_number'] for p in
                  DBService.run("SELECT Phone_number FROM Phone_Numbers WHERE Email=?", (email,), fetchall=True)]
        return cls(row['Email'], row['First_Name'], row['Last_Name'], row['Password'], row['Birth_Date'],
                   row['User_Passport'], row['Registered_Date'], phones)

    @staticmethod
    def migrate_guest_data(email):
        """
        Checks if an email belongs to a guest and migrates their orders
        and phone records to the registered user type.
        """
        was_guest = DBService.run("SELECT 1 FROM Guests WHERE Email=?", (email,), fetchone=True)
        if was_guest:
            # Delete old guest phone records to avoid duplicates during registration
            DBService.run("DELETE FROM Phone_Numbers WHERE Email = ?", (email,))
            # Update orders to link them to a 'Registered' account
            DBService.run("UPDATE Orders SET Customer_type = 'Registered' WHERE Customer_email = ?", (email,))
            # Delete the guest entry
            DBService.run("DELETE FROM Guests WHERE Email = ?", (email,))
        return was_guest

class Guest(Customer):
    """ Represents a user booking as a guest without prior registration. """
    def __init__(self, email, first_name, last_name, phone_numbers):
        super().__init__(email, first_name, last_name, phone_numbers, customer_type="Guest")

    def save_to_db(self):
        """ Saves basic guest info and phone numbers to the database. """
        DBService.run(
            "INSERT INTO Guests (Email, Customer_type, First_Name, Last_Name) VALUES (?, ?, ?, ?)",
            (self.email, self.customer_type, self.first_name, self.last_name)
        )
        self.save_phone_numbers("Phone_Numbers")

# ==================================================
# EMPLOYEE MODELS (EMPLOYEE, MANAGER, FLIGHT CREW)
# ==================================================
class Employee:
    """ Base class for all airline employees. """
    def __init__(self, employee_id, first_name, last_name, city, street, house_number, phone_number, start_date):
        self.employee_id = employee_id
        self.first_name = first_name
        self.last_name = last_name
        self.city = city
        self.street = street
        self.house_number = house_number
        self.phone_number = phone_number
        self.start_date = start_date


class Manager(Employee):
    def __init__(self, employee_id, first_name, last_name, city, street, house_number, phone_number, start_date,
                 password):
        super().__init__(employee_id, first_name, last_name, city, street, house_number, phone_number, start_date)
        self.password = password

    @staticmethod
    def login(employee_id, password):
        """ Validates manager credentials against the database. """
        row = DBService.run(
            "SELECT Employee_ID, Password, First_Name, Last_Name FROM Managers WHERE Employee_ID=?",
            (employee_id,), fetchone=True
        )
        if not row or row['Password'] != password:
            return None
        return row

    @staticmethod
    def add_flight_crew(employee_id, first_name, last_name, city, street, house_number, phone_number, start_date, role,
                        qualifications):
        """ Inserts a new flight crew member record into the FlightCrew table. """
        DBService.run(
            """
            INSERT INTO FlightCrew
            (Employee_ID, First_Name, Last_Name, City, Street, House_Number, Phone_Number, Start_Date, Role, Qualifications)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (employee_id, first_name, last_name, city, street, house_number, phone_number, start_date, role,
             qualifications),
        )
        return True

    @staticmethod
    def build_manager_dashboard(start_date=None, end_date=None):
        """
        Collects business statistics for the manager's dashboard.
        """
        assets = {"lists": {}, "totals": {}, "filters": {"start": start_date, "end": end_date}}

        # Define dynamic date filter
        params = []

        if start_date and end_date:
            # Applies selected range if filter is used
            date_filter = "AND Execute_DateTime BETWEEN ? AND ?"
            params = [start_date, end_date]
        else:
            # Default: All time (no additional date constraints)
            date_filter = ""

        # 1. Top 3 Employees (Flight hours - bypasses filter)
        assets["lists"]["top_employees"] = [
            {"name": f"{r['First_Name']} {r['Last_Name']}", "value": r['total_hours']}
            for r in DBService.run("""
                        SELECT fc.First_Name, fc.Last_Name, ROUND(SUM(r.Duration/60.0), 1) as total_hours
                        FROM FlightCrew fc
                        JOIN Flight_assigned fa ON fc.Employee_ID = fa.Employee_IDFK
                        JOIN Flights f ON fa.Flight_IDFK = f.Flight_ID
                        JOIN Routes r ON f.Origin_AirportFK = r.Origin_Airport
                        AND f.Destination_AirportFK = r.Destination_Airport
                        WHERE f.Status = 'Completed'
                        GROUP BY fc.Employee_ID
                        ORDER BY total_hours DESC
                        LIMIT 3
                    """, fetchall=True)
        ]

        # 2. Top 3 Customers (Revenue - bypasses filter)
        assets["lists"]["top_customers"] = [
            {"name": f"{r['fname']} {r['lname']}", "value": r['total_spent']}
            for r in DBService.run("""
                        SELECT COALESCE(ru.First_Name, g.First_Name) as fname,
                        COALESCE(ru.Last_Name, g.Last_Name) as lname,
                        ROUND(SUM(o.Total_Price), 2) as total_spent
                        FROM Orders o
                        LEFT JOIN RegisteredUser ru ON o.Customer_email = ru.Email
                        LEFT JOIN Guests g ON o.Customer_email = g.Email
                        WHERE o.Status IN ('Completed', 'Active')
                        GROUP BY o.Customer_email
                        ORDER BY total_spent DESC
                        LIMIT 3
                    """, fetchall=True)
        ]

        # 3. Top 3 Routes (Popularity - bypasses filter)
        assets["lists"]["top_routes"] = [
            {"name": f"{r['Origin_AirportFK']} → {r['Destination_AirportFK']}"}
            for r in DBService.run("""
                        SELECT f.Origin_AirportFK, f.Destination_AirportFK, COUNT(t.Order_IDFK) as ticket_count
                        FROM Tickets t
                        JOIN Flights f ON t.Flight_IDFK = f.Flight_ID
                        JOIN Orders o ON t.Order_IDFK = o.Order_ID
                        WHERE o.Status IN ('Completed', 'Active')
                        GROUP BY f.Origin_AirportFK, f.Destination_AirportFK
                        ORDER BY ticket_count DESC
                        LIMIT 3
                    """, fetchall=True)
        ]

        # 4. Total Revenue (Filtered period OR All Time)
        res_revenue = DBService.run(f"SELECT ROUND(SUM(Total_Price), 2) as total FROM Orders WHERE 1=1 {date_filter}",
                                    params, fetchone=True)
        assets["totals"]["revenue"] = res_revenue['total'] if res_revenue and res_revenue['total'] else 0

        # 5. Peak Months (Bypasses filter - fixed to trailing 1 year for relevance)
        month_names_map = {
            '01': 'January', '02': 'February', '03': 'March', '04': 'April',
            '05': 'May', '06': 'June', '07': 'July', '08': 'August',
            '09': 'September', '10': 'October', '11': 'November', '12': 'December'
        }

        raw_months = DBService.run("""
            SELECT strftime('%m', Execute_DateTime) as month_num, COUNT(*) as order_count
            FROM Orders
            WHERE Execute_DateTime >= date('now', '-1 year')
            GROUP BY month_num
            ORDER BY order_count DESC
            LIMIT 3
        """, fetchall=True)

        assets["lists"]["top_months"] = [
            {"name": month_names_map.get(r['month_num'], r['month_num'])}
            for r in raw_months
        ]

        # 6. Cancellation Rate (Filtered period OR All Time)
        res_cancel = DBService.run(f"""
                    SELECT ROUND((COUNT(CASE WHEN Status = 'Customer Cancellation' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 2) as rate
                    FROM Orders WHERE 1=1 {date_filter}
                """, params, fetchone=True)
        assets["totals"]["cancel_rate"] = res_cancel['rate'] if res_cancel and res_cancel['rate'] else 0

        return assets

class FlightCrew(Employee):
    """ Represents pilots and attendants. """
    def __init__(self, employee_id, first_name, last_name, city, street, house_number, phone_number, start_date, role,
                 qualifications):
        super().__init__(employee_id, first_name, last_name, city, street, house_number, phone_number, start_date)
        self.role = role
        self.qualifications = qualifications

# ==================================================
# 5. ASSET MODELS (AIRPLANE, FLIGHT, ROUTE)
# ==================================================
class Airplane:
    """ Represents an aircraft in the airline fleet. """

    def __init__(self, airplane_id, size, manufacturer):
        self.airplane_id = airplane_id
        self.size = size
        self.manufacturer = manufacturer

    @staticmethod
    def create_full_airplane(form_data):
        """
        Handles the logic of creating airplane entries for different classes.
        """
        airplane_id = form_data.get("airplane_id")
        manufacturer = form_data.get("manufacturer")
        size = form_data.get("size")
        purchase_date = form_data.get("purchase_date")

        # 1. Prepare and save Economy class (always required)
        eco_success = Airplane.add_new_airplane({
            "airplane_id": airplane_id,
            "class_type": "Economy",
            "manufacturer": manufacturer,
            "size": size,
            "purchase_date": purchase_date,
            "num_rows": form_data.get("eco_rows"),
            "num_cols": form_data.get("eco_cols")
        })

        # 2. Prepare and save Business class only for large planes
        if eco_success and size == "large":
            return Airplane.add_new_airplane({
                "airplane_id": airplane_id,
                "class_type": "Business",
                "manufacturer": manufacturer,
                "size": size,
                "purchase_date": purchase_date,
                "num_rows": form_data.get("bus_rows"),
                "num_cols": form_data.get("bus_cols")
            })

        return eco_success

    @staticmethod
    def add_new_airplane(data):
        """ Registers a new airplane and its seating layout in the database. """
        DBService.run(
            """
            INSERT INTO Airplanes
            (Airplane_ID, Class_Type, Manufacturer, Size, Purchase_Date, Number_of_rows, Number_of_columns)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["airplane_id"], data["class_type"], data["manufacturer"],
                data["size"], data["purchase_date"], data["num_rows"], data["num_cols"]
            )
        )
        return True


class Flight:
    """
        Core logic for flight management. Handles search,
        resource availability, and seat map generation.
    """
    def __init__(self, flight_id, class_type, airplane_id, origin, destination, departure_time, arrival_time,
                 duration, price_regular, price_business, status):
        self.flight_id = flight_id
        self.class_type = class_type
        self.airplane_id = airplane_id
        self.origin = origin
        self.destination = destination
        self.departure_time = departure_time
        self.arrival_time = arrival_time
        self.duration = duration
        self.price_regular = price_regular
        self.price_business = price_business
        self.status = status


    @property
    def formatted_duration(self):
        """
        Converts duration in minutes to a human-readable HH:MM format.
        """
        total_mins = int(self.duration)
        hours = total_mins // 60
        minutes = total_mins % 60
        return f"{hours}:{minutes:02d}"

    def calculate_total_price(self, selected_seats):
        """
        Calculates the total price for a list of selected seats based on their class type.
        Format of seats expected: 'Class-Row-Col'
        """
        total = 0
        for seat in selected_seats:
            class_type = seat.split('-')[0]
            if class_type == "Economy":
                total += self.price_regular or 0
            elif class_type == "Business":
                total += self.price_business or 0
        return total

    @staticmethod
    def get_display_status(db_status, arrival_time):
        if not arrival_time:
            return db_status
        now = datetime.now()
        if isinstance(arrival_time, str):
            arrival_time = arrival_time.split('.')[0]
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                try:
                    arrival_time = datetime.strptime(arrival_time, fmt)
                    break
                except ValueError:
                    continue
        if db_status == 'Canceled':
            return 'Canceled'
        if db_status == 'Active' and arrival_time <= now:
            return 'Completed'
        return db_status

    @staticmethod
    def search(filters=None, for_manager=False):
        query = """
            SELECT
                f1.Flight_ID,
                MAX(f1.Origin_AirportFK) as Origin_AirportFK,
                MAX(f1.Destination_AirportFK) as Destination_AirportFK,
                MAX(f1.Departure_Time) as Departure_Time,
                MAX(COALESCE(datetime(f1.Departure_Time, '+' || r.Duration || ' minutes'), f1.Departure_Time)) as Arrival_Time,
                MAX(f1.Status) as status,
                MAX(CASE WHEN f1.Class_TypeFK = 'Economy' THEN f1.Status END) as eco_status,
                MAX(CASE WHEN f1.Class_TypeFK = 'Business' THEN f1.Status END) as bus_status
            FROM Flights f1
            LEFT JOIN Routes r ON f1.Origin_AirportFK = r.Origin_Airport
                               AND f1.Destination_AirportFK = r.Destination_Airport
            WHERE 1=1
        """
        params = []
        if not for_manager:
            query += " AND f1.Status = 'Active' AND f1.Departure_Time > CURRENT_TIMESTAMP "

        if filters:
            if filters.get("departure_date"):
                query += " AND DATE(f1.Departure_Time) = ?"
                params.append(filters["departure_date"])
            if filters.get("origin"):
                query += " AND f1.Origin_AirportFK = ?"
                params.append(filters["origin"])
            if filters.get("destination"):
                query += " AND f1.Destination_AirportFK = ?"
                params.append(filters["destination"])

        query += " GROUP BY f1.Flight_ID "
        if filters and filters.get("status") and filters["status"] != "":
            st = filters["status"]
            if st == 'Active':
                query += " HAVING (MAX(CASE WHEN f1.Class_TypeFK = 'Economy' THEN f1.Status END) = 'Active' OR MAX(CASE WHEN f1.Class_TypeFK = 'Business' THEN f1.Status END) = 'Active')"
            elif st == 'Fully Booked':
                query += " HAVING (MAX(CASE WHEN f1.Class_TypeFK = 'Economy' THEN f1.Status END) = 'Fully Booked' OR MAX(CASE WHEN f1.Class_TypeFK = 'Business' THEN f1.Status END) = 'Fully Booked')"
            else:
                query += " HAVING MAX(f1.Status) = ?"
                params.append(st)

        rows = DBService.run(query, params, fetchall=True)

        results = []
        for row in rows:
            def safe_strptime(val):
                if not val: return None
                if isinstance(val, datetime): return val
                s = str(val).split('.')[0]
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                    try:
                        return datetime.strptime(s, fmt)
                    except ValueError:
                        continue
                return None

            dep_time = safe_strptime(row['Departure_Time'])
            arr_time = safe_strptime(row['Arrival_Time'])

            display_status = Flight.get_display_status(row['status'], arr_time)

            if for_manager and display_status not in ['Canceled', 'Completed']:
                if row['eco_status'] == 'Fully Booked' and row['bus_status'] == 'Active':
                    display_status = "Economy: Full | Business: Active"
                elif row['eco_status'] == 'Active' and row['bus_status'] == 'Fully Booked':
                    display_status = "Economy: Active | Business: Full"

            results.append({
                "flight_id": row['Flight_ID'],
                "origin": row['Origin_AirportFK'],
                "destination": row['Destination_AirportFK'],
                "departure_time": dep_time,
                "arrival_time": arr_time,
                "status": row['status'],
                "display_status": display_status
            })
        return results

    @staticmethod
    def get_by_id(flight_id, class_type=None):
        """ Fetches full flight details with robust date parsing. """
        query = """
            SELECT f.*, r.Duration,
                   datetime(f.Departure_Time, '+' || r.Duration || ' minutes') as Arrival_Time
            FROM Flights f
            LEFT JOIN Routes r ON f.Origin_AirportFK = r.Origin_Airport
                               AND f.Destination_AirportFK = r.Destination_Airport
            WHERE f.Flight_ID = ?
        """
        rows = DBService.run(query, (flight_id,), fetchall=True)

        if not rows:
            return None

        data = rows[0]

        def to_dt(val):
            if not val: return None
            if isinstance(val, datetime): return val
            s = str(val).split('.')[0]
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        dep_time = to_dt(data['Departure_Time'])
        arr_time = to_dt(data['Arrival_Time'])

        price_regular = None
        price_business = None
        eco_status = 'Active'
        bus_status = 'Active'

        for r in rows:
            if r['Economy_price'] is not None:
                price_regular = r['Economy_price']
                eco_status = r['Status']
            if r['Business_price'] is not None:
                price_business = r['Business_price']
                bus_status = r['Status']

        f_obj = Flight(
            flight_id=data['Flight_ID'],
            class_type=class_type or 'Economy',
            airplane_id=data['Airplane_IDFK'],
            origin=data['Origin_AirportFK'],
            destination=data['Destination_AirportFK'],
            departure_time=dep_time,
            arrival_time=arr_time,
            duration=data['Duration'],
            price_regular=price_regular,
            price_business=price_business,
            status=data['Status']
        )

        f_obj.display_status = Flight.get_display_status(data['Status'], arr_time)
        f_obj.eco_status = eco_status
        f_obj.bus_status = bus_status

        return f_obj

    def hours_to_departure(self):
        """ Calculates the remaining hours until the flight departs. """
        if not self.departure_time:
            return 0
        now = datetime.now()
        diff = self.departure_time - now
        return diff.total_seconds() / 3600

    @staticmethod
    def get_all_airports():
        """ Returns list of all airports that serve as an origin in existing routes. """
        query = "SELECT DISTINCT Origin_Airport FROM Routes"
        rows = DBService.run(query, fetchall=True)
        return [row['Origin_Airport'] for row in rows]

    @staticmethod
    def get_destinations_for_origin(origin):
        """ Returns specific destinations reachable from a given origin airport. """
        query = "SELECT DISTINCT Destination_Airport FROM Routes WHERE Origin_Airport = ?"
        rows = DBService.run(query, (origin,), fetchall=True)
        return [row['Destination_Airport'] for row in rows]

    @staticmethod
    def get_route_duration(origin, destination):
        """ Returns the flying time (in hours) between two airports. """
        row = DBService.run(
            "SELECT Duration FROM Routes WHERE Origin_Airport = ? AND Destination_Airport = ?",
            (origin, destination),
            fetchone=True
        )
        return row['Duration'] if row else None

    @staticmethod
    def get_available_airplanes(origin, db, flight_type, departure_time_str):
        """
        Query to find airplanes that are either idle or currently
        at the origin airport and free during the requested timeframe.
        """
        req_dep_time = datetime.fromisoformat(departure_time_str)
        query = """
            SELECT DISTINCT Airplane_ID, Size, Manufacturer
            FROM Airplanes
            WHERE (
                Airplane_ID NOT IN (SELECT DISTINCT Airplane_IDFK FROM Flights)
                OR
                Airplane_ID IN (
                    SELECT f1.Airplane_IDFK
                    FROM Flights f1
                    WHERE f1.Destination_AirportFK = ?
                      AND f1.Arrival_Time <= ?
                      AND f1.Arrival_Time = (
                          SELECT MAX(f2.Arrival_Time)
                          FROM Flights f2
                          WHERE f2.Airplane_IDFK = f1.Airplane_IDFK
                      )
                )
            )
            AND Airplane_ID NOT IN (
                SELECT Airplane_IDFK FROM Flights
                WHERE Status = 'Active'
                AND (Departure_Time <= ? AND Arrival_Time >= ?)
            )
        """
        if flight_type == 'long':
            query += " AND Size='large'"

        rows = db.run(query, (origin, req_dep_time, req_dep_time, req_dep_time), fetchall=True)
        return rows

    @staticmethod
    def get_available_crew(db, origin, flight_type, departure_time_str):
        """
        Query to find available pilots and attendants based on their
        location, flight history, and required qualifications.
        We use a helper function 'get_crew_by_role' to avoid writing the same
        long SQL query twice (once for pilots and once for attendants).
        """
        req_dep_time = datetime.fromisoformat(departure_time_str)
        qualification_filter = "AND Qualifications=1" if flight_type == 'long' else ""

        def get_crew_by_role(role):
            query = f"""
                    SELECT Employee_ID, First_Name, Last_Name
                    FROM FlightCrew
                    WHERE Role = ?
                    {qualification_filter}
                    AND (
                        Employee_ID NOT IN (SELECT Employee_IDFK FROM Flight_assigned)
                        OR
                        Employee_ID IN (
                            SELECT fa.Employee_IDFK
                            FROM Flight_assigned fa
                            JOIN Flights f ON fa.Flight_IDFK = f.Flight_ID
                            WHERE f.Destination_AirportFK = ?
                              AND f.Arrival_Time <= ?
                              AND f.Arrival_Time = (
                                  SELECT MAX(f_inner.Arrival_Time)
                                  FROM Flights f_inner
                                  JOIN Flight_assigned fa_inner ON f_inner.Flight_ID = fa_inner.Flight_IDFK
                                  WHERE fa_inner.Employee_IDFK = fa.Employee_IDFK
                              )
                        )
                    )
                    AND Employee_ID NOT IN (
                        SELECT fa2.Employee_IDFK
                        FROM Flight_assigned fa2
                        JOIN Flights f2 ON fa2.Flight_IDFK = f2.Flight_ID
                        WHERE f2.Status IN ('Active', 'Fully Booked')
                        AND (f2.Departure_Time <= ? AND f2.Arrival_Time >= ?)
                    )
                """
            return db.run(query, (role, origin, req_dep_time, req_dep_time, req_dep_time), fetchall=True)

        pilots = get_crew_by_role('Pilot')
        attendants = get_crew_by_role('Attendant')

        p_list = [{"employee_id": r['Employee_ID'], "first_name": r['First_Name'], "last_name": r['Last_Name']} for r in
                  pilots]
        a_list = [{"employee_id": r['Employee_ID'], "first_name": r['First_Name'], "last_name": r['Last_Name']} for r in
                  attendants]

        return p_list, a_list

    @staticmethod
    def determine_flight_type(duration_mins):
        """ Returns 'long' for flights over 6 hours (360 mins), otherwise 'short'. """
        return "long" if (duration_mins or 0) > 360 else "short"

    @staticmethod
    def validate_crew_requirements(airplane_size, num_pilots, num_attendants):
        """
        Checks if the crew meets safety standards based on aircraft size.
        Returns (is_valid, error_message).
        """
        if airplane_size == 'large':
            if num_pilots != 3:
                return False, "Large aircraft requires exactly 3 pilots."
            if num_attendants != 6:
                return False, "Large aircraft requires exactly 6 attendants."
        else:
            if num_pilots != 2:
                return False, "Small aircraft requires exactly 2 pilots."
            if num_attendants != 3:
                return False, "Small aircraft requires exactly 3 attendants."

        return True, None

    @staticmethod
    def create_flight(origin, destination, departure_time, arrival_time, airplane_id, pilot_ids, attendant_ids, db,
                      price_regular, price_business):
        """
        Creates a new flight entry and assigns the chosen crew members.
        """
        # Generate a random Flight ID (e.g., AB123)
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        numbers = ''.join(random.choices(string.digits, k=3))

        flight_id = f"{letters}{numbers}"
        # Ensure ID uniqueness: regenerate if already exists in DB
        while db.run("SELECT 1 FROM Flights WHERE Flight_ID = ?", (flight_id,), fetchone=True):
            letters = ''.join(random.choices(string.ascii_uppercase, k=2))
            numbers = ''.join(random.choices(string.digits, k=3))
            flight_id = f"{letters}{numbers}"

        clean_dep = str(departure_time).replace('T', ' ')[:16]
        clean_arr = str(arrival_time).replace('T', ' ')[:16]

        db.run(
            """
            INSERT INTO Flights
            (Flight_ID, Class_TypeFK, Airplane_IDFK, Origin_AirportFK, Destination_AirportFK,
             Departure_Time, Arrival_Time, Economy_price, Status)
            VALUES (?, 'Economy', ?, ?, ?, ?, ?, ?, 'Active')
            """,
            (flight_id, airplane_id, origin, destination, clean_dep, clean_arr, price_regular)
        )

        if price_business and float(price_business) > 0:
            db.run(
                """
                INSERT INTO Flights
                (Flight_ID, Class_TypeFK, Airplane_IDFK, Origin_AirportFK, Destination_AirportFK,
                 Departure_Time, Arrival_Time, Business_price, Status)
                VALUES (?, 'Business', ?, ?, ?, ?, ?, ?, 'Active')
                """,
                (flight_id, airplane_id, origin, destination, clean_dep, clean_arr, price_business)
            )

        for eid in pilot_ids + attendant_ids:
            db.run("INSERT INTO Flight_assigned (Employee_IDFK, Flight_IDFK) VALUES (?, ?)", (eid, flight_id))

    def get_seat_map(self):
        # Get the plane layout from the database
        classes = DBService.run(
            "SELECT Class_Type, Number_of_rows, Number_of_columns FROM Airplanes WHERE Airplane_ID=?",
            (self.airplane_id,), fetchall=True)

        # Get only seats from 'Active' orders (ignore canceled ones)
        booked = DBService.run(
            "SELECT t.Row_Num, t.Col_Num FROM Tickets t JOIN Orders o ON t.Order_IDFK = o.Order_ID WHERE t.Flight_IDFK = ? AND o.Status = 'Active'",
            (self.flight_id,), fetchall=True)

        # We use a set of tuples for the booked seats because searching a set is much faster
        booked_set = {(r['Row_Num'], str(r['Col_Num']).strip().upper()) for r in booked}

        seat_map = {}
        availability = {}
        current_row_start = 1

        for config in classes:
            c_type = config['Class_Type']
            rows_list = []
            has_free_seat = False

            # Build the grid row by row
            for r in range(current_row_start, current_row_start + config['Number_of_rows']):
                row_seats = []
                for c in range(1, config['Number_of_columns'] + 1):
                    # chr(64 + c) turns numbers into letters: 1 -> A, 2 -> B, etc.
                    col = chr(64 + c)
                    is_avail = (r, col) not in booked_set
                    if is_avail: has_free_seat = True

                    row_seats.append({"row": r, "column": col, "available": is_avail})
                rows_list.append(row_seats)

            seat_map[c_type] = rows_list
            availability[c_type] = has_free_seat

            # Move the row counter forward so the next class starts where this one ended
            current_row_start += config['Number_of_rows']

        return seat_map, availability

    @staticmethod
    def get_popular_destinations():
        """ Finds the top destinations with the cheapest active flights for the homepage. """
        pool = {
            'JFK': {'name': 'New York',
                    'img': 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?q=80&w=400'},
            'LHR': {'name': 'London', 'img': 'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?q=80&w=400'},
            'BKK': {'name': 'Bangkok',
                    'img': 'https://images.unsplash.com/photo-1583417319070-4a69db38a482?q=80&w=400'},
            'DXB': {'name': 'Dubai', 'img': 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?q=80&w=400'},
            'FCO': {'name': 'Rome', 'img': 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?q=80&w=400'},
            'CDG': {'name': 'Paris', 'img': 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?q=80&w=400'}
        }

        dest_data = []
        for code, info in pool.items():
            query = """
                    SELECT MIN(Economy_price) as min_price
                    FROM Flights
                    WHERE Destination_AirportFK = ? AND Status = 'Active' AND Departure_Time > CURRENT_TIMESTAMP
                """
            res = DBService.run(query, (code,), fetchone=True)

            if res and res['min_price']:
                dest_data.append({
                    'code': code,
                    'name': info['name'],
                    'img': info['img'],
                    'price': int(res['min_price'])
                })
                if len(dest_data) == 3:
                    break
        return dest_data

# ==================================================
# ORDER
# ==================================================
class Order:
    """ Handles retrieval and updates of flight booking records. """
    def __init__(self, order_id, flight_id, customer_email, status, execute_datetime):
        self.order_id = order_id
        self.flight_id = flight_id
        self.customer_email = customer_email
        self.status = status
        self.execute_datetime = execute_datetime

    @staticmethod
    def get_display_status(db_status, arrival_time):
        now = datetime.now()
        if isinstance(arrival_time, str):
            arrival_time = arrival_time.split('.')[0]
            try:
                arrival_time = datetime.strptime(arrival_time, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                arrival_time = datetime.strptime(arrival_time, '%Y-%m-%d %H:%M')
        if db_status in ['Customer Cancellation', 'Canceled', 'Completed']:
            return db_status
        if db_status == 'Active' and arrival_time <= now:
            return 'Completed'
        return db_status

    @staticmethod
    def get_seats_by_order(order_id):
        """
        Fetches all seats for a specific order and groups them by class type.
        Returns a dictionary: {'Business': ['1A', '1B'], 'Economy': ['10C']}
        """
        query = """
                    SELECT t.Row_Num, t.Col_Num, a.Class_Type, a.Number_of_rows
                    FROM Tickets t
                    JOIN Flights f ON t.Flight_IDFK = f.Flight_ID
                    JOIN Airplanes a ON f.Airplane_IDFK = a.Airplane_ID
                    WHERE t.Order_IDFK = ?
                """
        rows = DBService.run(query, (order_id,), fetchall=True)

        if not rows:
            return {'Business': [], 'Economy': []}

        business_rows_limit = 0
        for r in rows:
            if r['Class_Type'] == 'Business':
                business_rows_limit = r['Number_of_rows']
                break

        grouped_seats = {'Business': [], 'Economy': []}
        seen_tickets = set()
        for r in rows:
            ticket_key = (r['Row_Num'], r['Col_Num'])
            if ticket_key in seen_tickets:
                continue
            seen_tickets.add(ticket_key)

            seat_str = f"{r['Row_Num']}{r['Col_Num']}"
            if r['Row_Num'] <= business_rows_limit:
                grouped_seats['Business'].append(seat_str)
            else:
                grouped_seats['Economy'].append(seat_str)

        return grouped_seats

    @staticmethod
    def get_guest_orders(order_id, email):
        """ Retrieves guest orders and converts dates to objects for unified handling. """
        query = """
               SELECT DISTINCT o.Order_ID, o.Flight_IDFK, o.Total_Price, o.Status,
                      o.Execute_DateTime,
                      f.Departure_Time,
                      datetime(f.Departure_Time, '+' || r.Duration || ' minutes') as Arrival_Time
               FROM Orders o
               JOIN Flights f ON o.Flight_IDFK = f.Flight_ID
               JOIN Routes r ON f.Origin_AirportFK = r.Origin_Airport
                             AND f.Destination_AirportFK = r.Destination_Airport
               WHERE o.Order_ID = ? AND o.Customer_email = ?
            """
        rows = DBService.run(query, (order_id, email), fetchall=True)

        results = []
        for r in rows:
            def to_dt(val):
                if not val: return None
                if isinstance(val, datetime): return val
                s = str(val).split('.')[0]
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                    try: return datetime.strptime(s, fmt)
                    except: continue
                return None

            dep = to_dt(r['Departure_Time'])
            arr = to_dt(r['Arrival_Time'])
            exe = to_dt(r['Execute_DateTime'])

            results.append({
                "order_id": r['Order_ID'],
                "flight_id": r['Flight_IDFK'],
                "total_price": r['Total_Price'],
                "status": r['Status'],
                "display_status": Order.get_display_status(r['Status'], arr),
                "order_date": exe,
                "departure_time": dep,
                "arrival_time": arr
            })
        return results

    @staticmethod
    def get_user_orders(email):
        """ Retrieves all orders associated with a registered user. """
        query = """
               SELECT DISTINCT o.Order_ID, o.Flight_IDFK, o.Total_Price, o.Status,
                      o.Execute_DateTime, f.Departure_Time,
                      datetime(f.Departure_Time, '+' || r.Duration || ' minutes') as Arrival_Time
               FROM Orders o
               JOIN Flights f ON o.Flight_IDFK = f.Flight_ID
               JOIN Routes r ON f.Origin_AirportFK = r.Origin_Airport
                             AND f.Destination_AirportFK = r.Destination_Airport
               WHERE o.Customer_email = ?
            """
        rows = DBService.run(query, (email,), fetchall=True)

        results = []
        for r in rows:
            def to_dt(val):
                if not val: return None
                if isinstance(val, datetime): return val
                s = str(val).split('.')[0]
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                    try: return datetime.strptime(s, fmt)
                    except: continue
                return None

            dep = to_dt(r['Departure_Time'])
            arr = to_dt(r['Arrival_Time'])
            exe = to_dt(r['Execute_DateTime'])

            results.append({
                "order_id": r['Order_ID'],
                "flight_id": r['Flight_IDFK'],
                "total_price": r['Total_Price'],
                "status": r['Status'],
                "display_status": Order.get_display_status(r['Status'], arr),
                "order_date": exe,
                "departure_time": dep,
                "arrival_time": arr,
                "customer_email": email
            })
        return results

    @staticmethod
    def update_order(order_id, status=None, total_price=None):
        """ Updates order status or price in the database. """
        set_clauses = []
        params = []
        if status is not None:
            set_clauses.append("Status=?")
            params.append(status)
        if total_price is not None:
            set_clauses.append("Total_Price=?")
            params.append(total_price)
        if not set_clauses: return
        query = f"UPDATE Orders SET {', '.join(set_clauses)} WHERE Order_ID=?"
        params.append(order_id)
        DBService.run(query, tuple(params))

    @staticmethod
    def create_full_order(flight_id, customer_email, customer_type, total_price, selected_seats):
        """
        Processes the entire order: creates the record, issues tickets, and updates flight status.
        """
        res = DBService.run("SELECT MAX(Order_ID) as max_id FROM Orders", fetchone=True)
        order_id = (res['max_id'] or 0) + 1
        now_cleaned = datetime.now().replace(microsecond=0)

        DBService.run(
            """
            INSERT INTO Orders
            (Order_ID, Flight_IDFK, Customer_type, Customer_email, Execute_DateTime, Total_Price, Status)
            VALUES (?, ?, ?, ?, ?, ?, 'Active')
            """,
            (order_id, flight_id, customer_type, customer_email, now_cleaned, total_price)
        )

        for seat in selected_seats:
            class_type, row, column = seat.split('-')
            DBService.run(
                "INSERT INTO Tickets (Order_IDFK, Flight_IDFK, Row_Num, Col_Num) VALUES (?, ?, ?, ?)",
                (order_id, flight_id, int(row), column)
            )

        # Check if the flight became "Fully Booked"
        class_type_booked = selected_seats[0].split('-')[0]
        flight = Flight.get_by_id(flight_id)
        _, availability = flight.get_seat_map()  #We only need to check if there are free seats left.

        if not availability.get(class_type_booked):
            DBService.run(
                "UPDATE Flights SET Status = 'Fully Booked' WHERE Flight_ID = ? AND Class_TypeFK = ?",
                (flight_id, class_type_booked)
            )

        return order_id

# ==================================================
# ROUTE
# ==================================================
class Route:
    def __init__(self, origin, destination, duration):
        self.origin = origin
        self.destination = destination
        self.duration = duration

    @staticmethod
    def add_route(origin, destination, duration):
        """Saves a new flight path to the database. """
        exists = DBService.run(
            "SELECT 1 FROM Routes WHERE Origin_Airport = ? AND Destination_Airport = ?",
            (origin, destination),
            fetchone=True)
        if exists:
            return False, f"Route from {origin} to {destination} already exists."
        DBService.run(
            "INSERT INTO Routes (Origin_Airport, Destination_Airport, Duration) VALUES (?, ?, ?)",
            (origin, destination, duration))
        return True, "Route added successfully!"