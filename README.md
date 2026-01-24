# FlyTAU
FlyTau is a smart flight management and booking platform. It allows users to browse flights, select seats, and manage bookings effortlessly, while providing airline managers with advanced tools to oversee flight schedules, aircraft assets, and crew assignments.

**#KeyFetures**
For Passengers (Users & Guests):
Search Engine: A flight board that allows users to find available flights by filtering origin, destination, and dates.
Booking Options: Supports both registered accounts and guest-mode, so users can buy tickets quickly even without signing up.
Interactive Seat Selection: A dynamic seat map that displays availability in real-time and separates Business and Economy classes based on the airplane's configuration.
Account Dashboard: A place for users to view their past history and manage active bookings, including the ability to cancel flights.

For managers:
Configuration: Tools to add new aircraft and customize seating layouts (rows and columns) for different cabin classes.
Crew Assignment: A system for assigning pilots and attendants based on their current location, flight history, and specific qualifications for long flights.
Route Expansion: Interface for defining new flight paths and durations between international airports.
Business Intelligence Dashboard: Real-time reports for managers showing total revenue, peak months, and cancellation rates.

**#FileGuide**
main.py: The application's core, handling all web routes, user sessions.
utilise.py: Contains the core logic of the system. It uses Object-Oriented Programming (OOP).
visualization.py: A dedicated script that uses Pandas and Matplotlib to generate visual business reports.
flytau.sql: The database schema and initial data.
templates/: This folder contains all the HTML pages.
static/: It contains the styles.css file.
