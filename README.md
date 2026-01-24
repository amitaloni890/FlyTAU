# FlyTAU
FlyTau is a smart flight management and booking platform. It allows users to browse flights, select seats, and manage bookings effortlessly, while providing airline managers with advanced tools to oversee flight schedules, aircraft assets, and crew assignments.

**#KeyFetures**
For Passengers (Users & Guests):
Smart Flight Search: Users can filter the global flight board by origin, destination, and date directly from the dashboard.
Flexible Booking Flow: Support for both registered members and Guest Checkout, allowing quick purchases without an account.
Interactive Seat Selection: A dynamic seat map that displays availability in real-time and separates Business and Economy classes based on the airplane's configuration.
Personal Account Management: A dedicated area for users to view their booking history and active trips.

For managers:
Configuration: Tools to add new aircraft and customize seating layouts (rows and columns) for different cabin classes.
Crew Assignment: A smart system for assigning pilots and attendants based on their current location, flight history, and specific qualifications for long-haul flights.
Route Expansion: Interface for defining new flight paths and durations between international airports.
Business Intelligence Dashboard: Real-time reports for managers showing total revenue, peak months, and cancellation rates.

**#FileGuide**
main.py: The application's core, handling all web routes, user sessions, and connecting the frontend to the backend logic.
utilise.py: The system's "brain," using Object-Oriented Programming (OOP) to define how customers, flights, and orders behave.
visualization.py: A dedicated script that uses Pandas and Matplotlib to generate visual business reports.
flytau.sql: The database schema and initial data.
templates/: This folder contains all the HTML pages.
static/: It contains the styles.css file.
