CREATE TABLE Airplanes (
    Airplane_ID VARCHAR(20),
    Manufacturer VARCHAR(50),
    Size VARCHAR(20),
    Purchase_Date DATE,
    Class_Type VARCHAR(20), 
    Number_of_rows INTEGER,
    Number_of_columns INTEGER,
    PRIMARY KEY (Airplane_ID, Class_Type)
);

CREATE TABLE Routes (
    Origin_Airport VARCHAR(50),
    Destination_Airport VARCHAR(50),
    Duration INTEGER,
    PRIMARY KEY (Origin_Airport, Destination_Airport)
);

CREATE TABLE Flights (
    Flight_ID VARCHAR(10),
    Class_TypeFK VARCHAR(20),
    Airplane_IDFK VARCHAR(20),
    Origin_AirportFK VARCHAR(50),
    Destination_AirportFK VARCHAR(50),
    Departure_Time DATETIME,
    Arrival_time DATETIME,
    Economy_price FLOAT,
    Business_price FLOAT,
    Status VARCHAR(20),
    PRIMARY KEY (Flight_ID, Class_TypeFK),
    FOREIGN KEY (Airplane_IDFK, Class_TypeFK) REFERENCES Airplanes(Airplane_ID, Class_Type),
    FOREIGN KEY (Origin_AirportFK, Destination_AirportFK) REFERENCES Routes(Origin_Airport, Destination_Airport)
);

CREATE TABLE RegisteredUser (
    Email VARCHAR(100) PRIMARY KEY,
    Customer_type VARCHAR(20),
    User_Passport VARCHAR(20) UNIQUE,
    Password VARCHAR(255),
    First_Name VARCHAR(50),
    Last_Name VARCHAR(50),
    Birth_Date DATE,
    Registered_Date DATE
);

CREATE TABLE Guests (
    Email VARCHAR(100) PRIMARY KEY,
    Customer_type VARCHAR(20),
    First_Name VARCHAR(50),
    Last_Name VARCHAR(50)
);

CREATE TABLE Phone_Numbers (
    Email VARCHAR(100),
    Phone_number VARCHAR(20),
    Customer_type VARCHAR(20),
    PRIMARY KEY (Email, Phone_number)
);

CREATE TABLE Orders (
    Order_ID INTEGER PRIMARY KEY,
    Flight_IDFK VARCHAR(10),
    Customer_type VARCHAR(20),
    Customer_email VARCHAR(100),
    Execute_DateTime DATETIME,
    Total_Price FLOAT,
    Status VARCHAR(50),
    FOREIGN KEY (Flight_IDFK) REFERENCES Flights(Flight_ID)
);

CREATE TABLE Tickets (
    Order_IDFK INTEGER,
    Flight_IDFK VARCHAR(10),
    Row_Num INTEGER,
    Col_Num VARCHAR(1),
    PRIMARY KEY (Order_IDFK, Flight_IDFK, Row_Num, Col_Num),
    FOREIGN KEY (Order_IDFK) REFERENCES Orders(Order_ID),
    FOREIGN KEY (Flight_IDFK) REFERENCES Flights(Flight_ID)
);

CREATE TABLE FlightCrew (
    Employee_ID VARCHAR(50) PRIMARY KEY,
    First_Name VARCHAR(50),
    Last_Name VARCHAR(50),
    City VARCHAR(50),
    Street VARCHAR(50),
    House_Number INTEGER,
    Phone_Number VARCHAR(20),
    Start_Date DATE,
    Role VARCHAR(20),
    Qualifications BOOLEAN
);

CREATE TABLE Managers (
    Employee_ID VARCHAR(50) PRIMARY KEY,
    First_Name VARCHAR(50),
    Last_Name VARCHAR(50),
    City VARCHAR(50),
    Street VARCHAR(50),
    House_Number INTEGER,
    Phone_Number VARCHAR(20),
    Start_Date DATE,
    Password VARCHAR(255)
);

CREATE TABLE Flight_assigned (
    Employee_IDFK VARCHAR(50),
    Flight_IDFK VARCHAR(10),
    PRIMARY KEY (Employee_IDFK, Flight_IDFK),
    FOREIGN KEY (Employee_IDFK) REFERENCES FlightCrew(Employee_ID),
    FOREIGN KEY (Flight_IDFK) REFERENCES Flights(Flight_ID)
);

CREATE TRIGGER trg_phone_numbers_customer_check
BEFORE INSERT ON Phone_Numbers
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NEW.Customer_type = 'Registered' AND NOT EXISTS (SELECT 1 FROM RegisteredUser WHERE Email = NEW.Email)
            THEN RAISE(ABORT, 'Phone number must belong to an existing registered user')
        WHEN NEW.Customer_type = 'Guest' AND NOT EXISTS (SELECT 1 FROM Guests WHERE Email = NEW.Email)
            THEN RAISE(ABORT, 'Phone number must belong to an existing guest')
        WHEN NEW.Customer_type NOT IN ('Registered', 'Guest')
            THEN RAISE(ABORT, 'Invalid customer type')
    END;
END;

CREATE TRIGGER trg_orders_customer_check
BEFORE INSERT ON Orders
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NEW.Customer_type = 'Registered' AND NOT EXISTS (SELECT 1 FROM RegisteredUser WHERE Email = NEW.Customer_email)
            THEN RAISE(ABORT, 'Order must belong to an existing registered user')
        WHEN NEW.Customer_type = 'Guest' AND NOT EXISTS (SELECT 1 FROM Guests WHERE Email = NEW.Customer_email)
            THEN RAISE(ABORT, 'Order must belong to an existing guest')
        WHEN NEW.Customer_type NOT IN ('Registered', 'Guest')
            THEN RAISE(ABORT, 'Invalid customer type')
    END;
END;

INSERT INTO Airplanes VALUES 
('B747-11', 'Boeing', 'large', '2015-10-10', 'Business', 10, 6),
('B747-11', 'Boeing', 'large', '2015-10-10', 'Economy', 30, 6),
('A320-02', 'Airbus', 'large', '2019-07-10', 'Business', 3, 4),
('A320-02', 'Airbus', 'large', '2019-07-10', 'Economy', 20, 4),
('B787-09', 'Boeing', 'large', '2023-05-15', 'Business', 6, 6),
('B787-09', 'Boeing', 'large', '2023-05-15', 'Economy', 30, 6),
('A380-12', 'Airbus', 'large', '2022-01-01', 'Business', 12, 4),
('A380-12', 'Airbus', 'large', '2022-01-01', 'Economy', 25, 4),
('B777-14', 'Boeing', 'large', '2024-01-01', 'Business', 8, 6),
('B777-14', 'Boeing', 'large', '2024-01-01', 'Economy', 20, 6),
('B737-01', 'Boeing', 'large', '2018-03-15', 'Business', 15, 4),
('B737-01', 'Boeing', 'large', '2018-03-15', 'Economy', 30, 4),
('D900-08', 'Dassault', 'small', '2023-01-01', 'Economy', 10, 4),
('E175-13', 'Embraer', 'small', '2020-06-06', 'Economy', 15, 4),
('D500-12', 'Dassault', 'small', '2022-08-08', 'Economy', 12, 4),
('D333-12', 'Dassault', 'large', '2023-08-08', 'Economy', 12, 4),
('D333-12', 'Dassault', 'large', '2023-08-08', 'Business', 3, 4),
('B737-06', 'Boeing', 'small', '2021-12-12', 'Economy', 18, 6);

INSERT INTO Routes VALUES 
('JFK', 'LAX', 480), 
('LAX', 'ORD', 240), 
('ORD', 'JFK', 210),
('ATL', 'MIA', 120), 
('MIA', 'JFK', 180), 
('TLV', 'JFK', 690),
('JFK', 'TLV', 660), 
('TLV', 'LHR', 330), 
('LHR', 'TLV', 300), 
('LAX', 'DXB', 900),
('TLV', 'DXB', 210), 
('DXB', 'TLV', 180), 
('CDG', 'TLV', 270), 
('ORD', 'TLV', 600),
('TLV', 'BKK', 660), 
('FCO', 'TLV', 210), 
('TLV', 'FCO', 240),
('LCA', 'ATH', 105), 
('JFK', 'MIA', 200),
('TLV', 'BER', 240);

INSERT INTO Flights VALUES 
('AA101', 'Economy', 'B737-01', 'JFK', 'LAX', '2025-12-01 08:00:00', '2025-12-01 16:00:00', 200.0, NULL, 'Completed'),
('AA101', 'Business', 'B737-01', 'JFK', 'LAX', '2025-12-01 08:00:00', '2025-12-01 16:00:00', NULL, 600.0, 'Completed'),
('DL202', 'Economy', 'A320-02', 'LAX', 'ORD', '2026-01-05 09:00:00', '2026-01-05 13:00:00', 320.0, NULL, 'Completed'),
('DL202', 'Business', 'A320-02', 'LAX', 'ORD', '2026-01-05 09:00:00','2026-01-05 13:00:00', NULL, 850.0, 'Completed'),
('UA303', 'Economy', 'A380-12', 'ORD', 'JFK', '2025-08-03 07:00:00', '2025-08-03 10:30:00', 100.0, NULL, 'Completed'),
('UA303', 'Business', 'A380-12', 'ORD', 'JFK', '2025-08-03 07:00:00', '2025-08-03 10:30:00', NULL, 280.0, 'Completed'),
('SW404', 'Economy', 'D500-12', 'ATL', 'MIA', '2025-12-04 12:00:00', '2025-12-04 14:00:00', 200.0, NULL, 'Completed'),
('AA505', 'Economy', 'B787-09', 'MIA', 'JFK', '2025-12-05 10:00:00',  '2025-12-05 13:00:00', 310.0, NULL, 'Completed'),
('AA505', 'Business', 'B787-09', 'MIA', 'JFK', '2025-12-05 10:00:00', '2025-12-05 13:00:00', NULL, 820.0, 'Completed'),
('LY606', 'Economy', 'B787-09', 'JFK', 'TLV', '2026-05-10 10:00:00', '2026-05-10 21:00:00', 900.0, NULL, 'Active'),
('LY606', 'Business', 'B787-09', 'JFK', 'TLV', '2026-05-10 10:00:00', '2026-05-10 21:00:00', NULL, 1200.0, 'Fully Booked'),
('DX707', 'Economy', 'D900-08', 'TLV', 'DXB', '2026-04-12 08:00:00', '2026-04-12 11:30:00', 350.0, NULL, 'Active'),
('LY808', 'Economy', 'B747-11', 'JFK', 'TLV', '2025-11-20 22:00:00', '2025-11-21 09:00:00', 950.0, NULL, 'Completed'),
('LY808', 'Business', 'B747-11', 'JFK', 'TLV', '2025-11-20 22:00:00','2025-11-21 09:00:00', NULL, 3000.0, 'Completed'),
('BA909', 'Economy', 'B737-06', 'TLV', 'LHR', '2026-06-01 06:00:00', '2026-06-01 11:30:00', 450.0, NULL, 'Active'),
('LY110', 'Economy', 'B747-11', 'TLV', 'BKK', '2026-03-01 20:00:00', '2026-03-02 07:00:00', 1100.0, NULL, 'Active'),
('LY110', 'Business', 'B747-11', 'TLV', 'BKK', '2026-03-01 20:00:00', '2026-03-02 07:00:00', NULL, 4500.0, 'Active'),
('LY111', 'Economy', 'E175-13', 'TLV', 'FCO', '2025-10-15 09:00:00', '2025-10-15 13:00:00', 330.0, NULL, 'Completed'),
('AA112', 'Economy', 'B777-14', 'JFK', 'LAX', '2026-03-20 12:00:00', '2026-03-20 20:00:00', 400.0, NULL, 'Fully Booked'),
('AA112', 'Business', 'B777-14', 'JFK', 'LAX', '2026-03-20 12:00:00','2026-03-20 20:00:00', NULL, 1200.0, 'Active'),
('AF113', 'Economy', 'A320-02', 'ORD', 'TLV', '2026-03-15 14:00:00', '2026-03-16 00:00:00', 500.0, NULL, 'Active'),
('AF113', 'Business', 'A320-02', 'ORD', 'TLV', '2026-03-15 14:00:00', '2026-03-16 00:00:00', NULL, 1500.0, 'Active'),
('LY114', 'Economy', 'B737-01', 'LAX', 'DXB', '2025-12-25 10:00:00', '2025-12-26 01:00:00', 300.0, NULL, 'Canceled'),
('LY114', 'Business', 'B737-01', 'LAX', 'DXB', '2025-12-25 10:00:00', '2025-12-26 01:00:00', NULL, 500, 'Canceled'),
('LY115', 'Economy', 'D333-12', 'TLV', 'JFK', '2026-04-01 10:00:00', '2026-04-01 21:30:00', 880.0, NULL, 'Active'),
('LY115', 'Business', 'D333-12', 'TLV', 'JFK', '2026-04-01 10:00:00', '2026-04-01 21:30:00', NULL, 2900.0, 'Active');

INSERT INTO RegisteredUser VALUES 
('alice.smith@email.com', 'Registered', '11223344', 'pass1', 'Alice', 'Smith', '1990-01-15', '2025-01-01'),
('bob.johnson@email.com', 'Registered', '22334455', 'pass2', 'Bob', 'Johnson', '1985-02-20', '2025-02-10'),
('carol.williams@email.com', 'Registered', '33445566', 'pass3', 'Carol', 'Williams', '1992-03-05', '2025-03-15'),
('david.brown@email.com', 'Registered', '44556677', 'pass4', 'David', 'Brown', '1988-04-22', '2025-04-12'),
('eve.davis@email.com', 'Registered', '55667788', 'pass5', 'Eve', 'Davis', '1995-05-30', '2025-05-20'),
('frank.miller@email.com', 'Registered', '66778899', 'pass6', 'Frank', 'Miller', '1980-07-12', '2025-06-01'),
('grace.lee@email.com', 'Registered', '77889900', 'pass7', 'Grace', 'Lee', '1993-09-09', '2025-07-10'),
('henry.wilson@email.com', 'Registered', '88990011', 'pass8', 'Henry', 'Wilson', '1982-11-11', '2025-08-01'),
('isabel.clark@email.com', 'Registered', '99001122', 'pass9', 'Isabel', 'Clark', '1996-01-01', '2025-08-20'),
('jack.lewis@email.com', 'Registered', '10101010', 'pass10', 'Jack', 'Lewis', '1989-02-02', '2025-09-01'),
('kelly.hall@email.com', 'Registered', '12121212', 'pass11', 'Kelly', 'Hall', '1991-03-03', '2025-09-15'),
('liam.young@email.com', 'Registered', '13131313', 'pass12', 'Liam', 'Young', '1994-04-04', '2025-10-01'),
('mia.king@email.com', 'Registered', '14141414', 'pass13', 'Mia', 'King', '1997-05-05', '2025-10-15'),
('noah.wright@email.com', 'Registered', '15151515', 'pass14', 'Noah', 'Wright', '1987-06-06', '2025-11-01'),
('olivia.hill@email.com', 'Registered', '16161616', 'pass15', 'Olivia', 'Hill', '1992-07-07', '2025-11-20');

INSERT INTO Guests VALUES 
('guest1@email.com', 'Guest', 'Tamar', 'Gur'), 
('guest2@email.com', 'Guest', 'Amit', 'Aloni'),
('guest3@email.com', 'Guest', 'Ariel', 'Kalfus'), 
('guest4@email.com', 'Guest', 'Shir', 'Tzuk'),
('guest5@email.com', 'Guest', 'Atalia', 'Shavit'), 
('guest6@email.com', 'Guest', 'Dan', 'Cohen'),
('guest7@email.com', 'Guest', 'Noa', 'Levy'), 
('guest8@email.com', 'Guest', 'Itay', 'Bar'),
('guest9@email.com', 'Guest', 'Maya', 'Peled'), 
('guest10@email.com', 'Guest', 'Yoni', 'Ziv'),
('guest11@email.com', 'Guest', 'Gal', 'Sela'), 
('guest12@email.com', 'Guest', 'Adi', 'Ron'),
('guest13@email.com', 'Guest', 'Ronit', 'Tal'), 
('guest14@email.com', 'Guest', 'Guy', 'Harel'),
('guest15@email.com', 'Guest', 'Rina', 'Aviv');

INSERT INTO Phone_Numbers VALUES 
('alice.smith@email.com', '11234567890', 'Registered'), 
('guest1@email.com', '04788889991', 'Guest'),
('bob.johnson@email.com', '12345678901', 'Registered'), 
('guest2@email.com', '05734578290', 'Guest'),
('carol.williams@email.com', '13456789012', 'Registered'), 
('guest3@email.com', '09993782913', 'Guest'),
('david.brown@email.com', '14567890123', 'Registered'), 
('guest4@email.com', '03345678924', 'Guest'),
('eve.davis@email.com', '15678901234', 'Registered'), 
('guest5@email.com', '09864425361', 'Guest'),
('frank.miller@email.com', '0506666777', 'Registered'), 
('guest6@email.com', '0521234567', 'Guest'),
('grace.lee@email.com', '0507777888', 'Registered'), 
('isabel.clark@email.com', '0547778898', 'Registered'),
('jack.lewis@email.com', '0537778898', 'Registered'), 
('kelly.hall@email.com', '0537668898', 'Registered'),
('mia.king@email.com', '0544448898', 'Registered'), 
('noah.wright@email.com', '0555558898', 'Registered'),
('olivia.hill@email.com', '0544445555', 'Registered'), 
('guest7@email.com', '0547778899', 'Guest'),
('guest8@email.com', '0567898899', 'Guest'), 
('guest9@email.com', '0777778899', 'Guest'), 
('guest10@email.com', '0541778899', 'Guest'),
('guest11@email.com', '0547771111', 'Guest'), 
('guest12@email.com', '0532778899', 'Guest'),  
('guest13@email.com', '0533338899', 'Guest'),
('guest14@email.com', '0512378899', 'Guest'), 
('guest15@email.com', '066678899', 'Guest'),
('henry.wilson@email.com', '0508888999', 'Registered');

INSERT INTO FlightCrew VALUES 
('111111111', 'עמית', 'כהן', 'New York', 'Main St', 10, '1111111111', '2015-01-01', 'Pilot', TRUE),
('111111112', 'עמית', 'לוי', 'New York', 'Main St', 10, '1111111112', '2015-01-01', 'Pilot', TRUE),
('111111113', 'מאור', 'ברוכמן', 'New York', 'Main St', 10, '1111111113', '2015-01-01', 'Attendant', TRUE),
('111111117', 'גאיה', 'מעיין', 'New York', 'Main St', 10, '1111111117', '2015-01-01', 'Attendant', TRUE),
('111111118', 'מאיה', 'קיי', 'New York', 'Main St', 10, '1111111118', '2015-01-01', 'Attendant', FALSE),
('111111119', 'נסרין', 'קדרי', 'New York', 'Main St', 10, '1111111119', '2015-01-01', 'Attendant', FALSE),
('111111114', 'נטע', 'ברזילאי', 'New York', 'Main St', 10, '1111111114', '2015-01-01', 'Pilot', FALSE),
('102222222', 'עומר', 'לוי', 'Los Angeles', 'Second St', 20, '1222222222', '2016-02-01', 'Attendant', TRUE),
('103435679', 'אריאל', 'מור', 'Chicago', 'Third St', 30, '1333333333', '2017-03-01', 'Pilot', TRUE),
('104234567', 'לינדה', 'טיילור', 'Miami', 'Fourth St', 40, '1444444444', '2015-03-01', 'Attendant', TRUE),
('105123456', 'תמר', 'אנדרסון', 'Boston', 'Fifth St', 50, '1555555555', '2012-04-02', 'Pilot', FALSE),
('564738920', 'אנה', 'זק', 'Boston', 'Fifth St', 50, '1555554555', '2012-04-02', 'Pilot', TRUE),
('105123457', 'שירה', 'חן', 'Haifa', 'Abba', 8, '0507777777', '2019-06-06', 'Attendant', TRUE),
('105123458', 'דני', 'אלבז', 'Netanya', 'Nitza', 22, '0508888888', '2020-07-07', 'Pilot', TRUE),
('105123459', 'מיכל', 'לוי', 'Eilat', 'Hamar', 3, '0509999999', '2021-08-08', 'Attendant', TRUE),
('105123460', 'יובל', 'דיין', 'Tel Aviv', 'Herzl', 10, '0501112233', '2022-01-01', 'Pilot', TRUE),
('105123461', 'ניר', 'לוין', 'Ramat Gan', 'Bialik', 5, '0504445566', '2021-05-10', 'Pilot', TRUE),
('105123462', 'איתי', 'גרמן', 'Jerusalem', 'Jaffa', 12, '0507778899', '2023-02-15', 'Pilot', FALSE),
('105123463', 'רוני', 'סופרסטאר', 'Tel Aviv', 'Dizengoff', 100, '0509990011', '2018-11-20', 'Pilot', TRUE),
('105123464', 'נועה', 'קירל', 'Ra''anana', 'Ahuza', 45, '0521112233', '2024-01-01', 'Attendant', TRUE),
('105123465', 'יהונתן', 'מרגי', 'Tel Aviv', 'Rothschild', 12, '0524445566', '2024-02-01', 'Attendant', TRUE),
('105123466', 'שרית', 'חדד', 'Ashdod', 'Herzl', 30, '0527778899', '2024-03-01', 'Attendant', FALSE),
('105123467', 'עדן', 'בן זקן', 'Kiryat Shmona', 'North', 1, '0529990011', '2023-12-12', 'Attendant', TRUE),
('105123468', 'סטטיק', 'לירז', 'Haifa', 'Panorama', 8, '0520001122', '2024-04-01', 'Attendant', FALSE),
('105123469', 'בן אל', 'תבורי', 'Tel Aviv', 'Park', 5, '0523334455', '2024-04-01', 'Attendant', TRUE),
('105123470', 'רן', 'דנקר', 'Tel Aviv', 'Bograshov', 22, '0526667788', '2023-06-06', 'Attendant', TRUE),
('105123471', 'ניב', 'סולטן', 'Tel Aviv', 'Yarkon', 10, '0529998877', '2022-09-09', 'Attendant', TRUE),
('105123472', 'מאור', 'אדרי', 'Ramla', 'South', 3, '0521110022', '2021-07-07', 'Attendant', FALSE),
('105123473', 'עדן', 'חסון', 'Hadera', 'East', 9, '0524441133', '2024-05-05', 'Attendant', TRUE),
('105123474', 'אושר', 'כהן', 'Tel Aviv', 'Allenby', 15, '0527772244', '2024-06-06', 'Attendant', TRUE),
('105133475', 'ירדן', 'כהן', 'Tel Aviv', 'Hayarkon', 14, '0537772234', '2021-06-06', 'Attendant', False);

INSERT INTO Managers VALUES 
('211111111', 'Paul', 'Thomas', 'New York', 'Main St', 15, '1666666666', '2014-01-01', 'mgrpass1'),
('233333333', 'Susan', 'Jackson', 'Los Angeles', 'Second St', 25, '1777777777', '2015-02-01', 'mgrpass2'),
('288888888', 'Karen', 'White', 'Chicago', 'Third St', 35, '1888888888', '2016-03-01', 'mgrpass3'),
('204112222', 'Robert', 'Harris', 'Miami', 'Fourth St', 45, '1999999999', '2017-04-01', 'mgrpass4'),
('205555555', 'Nancy', 'Martin', 'Boston', 'Fifth St', 55, '1000000000', '2018-05-01', 'mgrpass5'),
('205555556', 'David', 'Cohen', 'Tel Aviv', 'Herzl', 10, '0526666667', '2019-06-01', 'mgrpass6'),
('205555557', 'Eran', 'Tsh', 'Tel Aviv', 'Uni', 1, '0527777778', '2015-01-01', 'mgrpass7'),
('205555558', 'Hadar', 'Eng', 'RG', 'Abba', 5, '0528888889', '2016-02-02', 'mgrpass8'),
('205555559', 'Sarah', 'Levi', 'Haifa', 'Abba', 12, '0529999990', '2020-07-01', 'mgrpass9'),
('205555560', 'Ben', 'Dror', 'Netanya', 'Nitza', 20, '0520000001', '2021-08-01', 'mgrpass10'),
('205555561', 'Maya', 'Arad', 'Herzliya', 'Sokolov', 15, '0521111122', '2022-09-01', 'mgrpass11'),
('205555562', 'Tom', 'Harel', 'Holon', 'Sokolov', 5, '0522222233', '2023-10-01', 'mgrpass12'),
('205555563', 'Dana', 'Ziv', 'Ashdod', 'Herzl', 30, '0523333344', '2024-11-01', 'mgrpass13'),
('205555564', 'Guy', 'Tal', 'Rehovot', 'Herzl', 100, '0524444455', '2015-12-01', 'mgrpass14'),
('205555565', 'Ronit', 'Bar', 'PT', 'Main', 22, '0525555566', '2016-01-01', 'mgrpass15');

INSERT INTO Orders VALUES 
(1, 'AA101', 'Registered', 'alice.smith@email.com', '2025-11-01 10:00:00', 30.0, 'Customer Cancellation'),
(2, 'DL202', 'Registered', 'bob.johnson@email.com', '2025-12-02 11:00:00', 16.0, 'Customer Cancellation'),
(3, 'UA303', 'Registered', 'carol.williams@email.com', '2024-12-03 12:00:00', 400.00, 'Completed'),
(4, 'LY606', 'Guest', 'guest5@email.com', '2025-11-04 13:00:00', 1200.0, 'Active'),
(5, 'AA505', 'Registered', 'eve.davis@email.com', '2025-11-05 14:00:00', 820.0, 'Completed'),
(6, 'DL202', 'Guest', 'guest4@email.com', '2025-10-02 11:00:00', 16.0, 'Customer Cancellation'),
(7, 'LY606', 'Registered', 'frank.miller@email.com', '2025-12-10 15:00:00', 900.0, 'Active'),
(8, 'LY808', 'Guest', 'guest1@email.com', '2025-11-15 09:00:00', 950.0, 'Completed'),
(9, 'LY111', 'Registered', 'grace.lee@email.com', '2025-09-30 14:00:00', 330.0, 'Completed'),
(10, 'LY110', 'Registered', 'jack.lewis@email.com', '2026-02-15 11:00:00', 4500.0, 'Active'),
(11, 'BA909', 'Guest', 'guest10@email.com', '2025-12-20 16:00:00', 450.0, 'Active'),
(12, 'AA112', 'Registered', 'olivia.hill@email.com', '2025-12-25 10:00:00', 1200.0, 'Active'),
(13, 'UA303', 'Guest', 'guest7@email.com', '2023-07-20 08:00:00', 14.0, 'Customer Cancellation'),
(14, 'LY115', 'Registered', 'noah.wright@email.com', '2026-01-28 12:00:00', 880.0, 'Active'),
(15, 'AF113', 'Guest', 'guest12@email.com', '2026-01-12 18:00:00', 1500.0, 'Active'),
(16, 'AF113', 'Registered', 'noah.wright@email.com', '2025-01-12 17:00:00', 75.0, 'Customer Cancellation'),
(17, 'LY111', 'Registered', 'grace.lee@email.com', '2025-01-30 14:00:00', 330.0, 'Completed'),
(18, 'LY111', 'Registered', 'frank.miller@email.com', '2025-01-15 14:00:00', 660.0, 'Completed'),
(19, 'LY110', 'Registered', 'carol.williams@email.com', '2024-03-15 11:00:00', 9000.0, 'Active'),
(20, 'UA303', 'Registered', 'olivia.hill@email.com', '2024-03-03 12:00:00', 280.0, 'Completed'),
(21, 'LY606', 'Guest', 'guest5@email.com', '2024-03-04 13:00:00', 60.0 , 'Customer Cancellation');

INSERT INTO Tickets VALUES 
(4, 'LY606', 1, 'B'), 
(5, 'AA505', 1, 'C'), 
(19, 'LY110', 5, 'C'), 
(19, 'LY110', 6, 'C'), 
(20, 'UA303', 10, 'C'),
(21, 'LY606', 4, 'A'),  
(3, 'UA303', 22, 'B'),
(3, 'UA303', 22, 'A'),
(3, 'UA303', 20, 'A'),
(3, 'UA303', 21, 'A'),
(7, 'LY606', 15, 'C'), 
(8, 'LY808', 20, 'D'), 
(9, 'LY111', 5, 'A'), 
(10, 'LY110', 1, 'D'), 
(11, 'BA909', 12, 'D'), 
(14, 'LY115', 30, 'A'), 
(12, 'AA112', 4, 'E'),
(2, 'DL202', 15, 'A'),
(6, 'DL202', 16, 'B'),
(13, 'UA303', 1, 'D'),
(1, 'AA101', 1, 'C'),
(16, 'AF113', 2, 'B'),
(17, 'LY111', 3, 'A'),
(18, 'LY111', 7, 'A'),
(18, 'LY111', 7, 'B'),
(15, 'AF113', 1, 'D');


INSERT INTO Flight_assigned VALUES 
('111111111', 'LY808'), ('111111111', 'UA303'),
('105123460', 'LY111'), 
('111111117', 'AA101'), ('111111117', 'DL202'),
('105123464', 'AA101'), ('105123464', 'DL202'), 
('103435679', 'LY808'), 
('105123463', 'LY808'),
('104234567', 'AA101'),
('105123467', 'AA101'), 
('564738920', 'LY808'),
('111111114', 'UA303'), 
('102222222', 'UA303'), 
('105123469', 'DL202'), 
('111111118', 'LY111'), 
('111111119', 'SW404'), 
('105123456', 'AA505'), 
('105123470', 'AA505'),
('105123472', 'SW404'), 
('105123457', 'LY111'), 
('105123458', 'LY110'), 
('105123461', 'AF113'), ('105123461', 'LY115'),
('105123459', 'LY808'), ('105123459', 'DX707'),
('105123471', 'AF113'), ('105123471', 'BA909'),
('111111112', 'AA112'),
('105123473', 'DX707'),
('105123474', 'LY606'), ('105123474', 'LY115'),
('105123462', 'BA909'), ('111111113', 'BA909'),
('105123466', 'BA909'), ('105123468', 'DX707');

SELECT 
    ROUND(AVG(occupancy_rate), 2) AS avg_occupancy_percent
FROM (
    SELECT 
        f.Flight_ID,
        (SELECT COUNT(*) 
         FROM Tickets t 
         JOIN Orders o ON t.Order_IDFK = o.Order_ID 
         WHERE t.Flight_IDFK = f.Flight_ID 
           AND o.Status IN ('Completed')) * 100.0 / 
        (SELECT SUM(a.Number_of_rows * a.Number_of_columns) 
         FROM Airplanes a 
         WHERE a.Airplane_ID = f.Airplane_IDFK) AS occupancy_rate
    FROM Flights f
    WHERE f.Status = 'Completed' 
    GROUP BY f.Flight_ID, f.Airplane_IDFK
) AS summary;

SELECT 
    a.Size AS Airplane_Size, 
    a.Manufacturer AS Airplane_Manufacturer, 
    a.Class_Type AS Cabin_Class,
    ROUND(SUM(o.Total_Price), 2) AS Total_Revenue
FROM Orders o
JOIN Flights f ON o.Flight_IDFK = f.Flight_ID
JOIN Airplanes a ON f.Airplane_IDFK = a.Airplane_ID AND f.Class_TypeFK = a.Class_Type
WHERE EXISTS (
    SELECT 1 FROM Tickets t 
    WHERE t.Order_IDFK = o.Order_ID 
    AND t.Flight_IDFK = f.Flight_ID
    AND (
        (a.Class_Type = 'Business' AND t.Row_Num <= a.Number_of_rows)
        OR 
        (a.Class_Type = 'Economy' AND t.Row_Num > 
            COALESCE((SELECT a2.Number_of_rows FROM Airplanes a2 
                      WHERE a2.Airplane_ID = a.Airplane_ID AND a2.Class_Type = 'Business'), 0))
    )
)
GROUP BY a.Size, a.Manufacturer, a.Class_Type
ORDER BY Total_Revenue DESC;

SELECT 
    fc.Employee_ID,
    fc.First_Name,
    fc.Last_Name,
    SUM(CASE WHEN r.Duration/60.0 <= 6 AND f.Status = 'Completed' THEN ROUND(r.Duration/60.0,1) ELSE 0 END) AS Short_Flight_Hours,
    SUM(CASE WHEN r.Duration/60.0 > 6 AND f.Status = 'Completed' THEN ROUND(r.Duration/60.0,1) ELSE 0 END) AS Long_Flight_Hours
FROM FlightCrew fc
LEFT JOIN Flight_assigned fa ON fc.Employee_ID = fa.Employee_IDFK
LEFT JOIN (
    SELECT DISTINCT Flight_ID, Origin_AirportFK, Destination_AirportFK, Status 
    FROM Flights
) f ON fa.Flight_IDFK = f.Flight_ID
LEFT JOIN Routes r ON f.Origin_AirportFK = r.Origin_Airport 
                 AND f.Destination_AirportFK = r.Destination_Airport
GROUP BY fc.Employee_ID, fc.First_Name, fc.Last_Name;

SELECT 
    strftime('%m', Execute_DateTime) AS Order_Month,
    strftime('%Y', Execute_DateTime) AS Order_Year,
    ROUND(
        SUM(CASE WHEN Status = 'Customer Cancellation' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 
        2
    ) AS Cancellation_Rate_Percent
FROM Orders
WHERE Execute_DateTime <= CURRENT_TIMESTAMP
GROUP BY Order_Year, Order_Month
HAVING SUM(CASE WHEN Status = 'Customer Cancellation' THEN 1 ELSE 0 END) > 0
ORDER BY Order_Year DESC, Order_Month DESC;

SELECT
    a.Airplane_ID,
    f_summary.Flight_Year AS "Year",
    f_summary.Flight_Month AS "Month",
    COALESCE(f_summary.Number_of_Completed_Flights, 0) AS "Num_of_Completed_Flights",
    COALESCE(f_summary.Number_of_Canceled_Flights, 0) AS "Num_of_Canceled_Flights",
    ROUND(COALESCE((f_summary.Number_of_Completed_Flights / 30.0) * 100, 0), 2) AS Utilization_Rate,
    COALESCE(dr.Dominant_Route, 'No Flights') AS "Dominant_Route"
FROM (
    SELECT DISTINCT Airplane_ID FROM Airplanes
) a
LEFT JOIN (
    SELECT
        Airplane_IDFK,
        strftime('%Y', Departure_Time) AS Flight_Year,
        strftime('%m', Departure_Time) AS Flight_Month,
        COUNT(DISTINCT CASE WHEN Status = 'Completed' THEN Flight_ID END) AS Number_of_Completed_Flights,
        COUNT(DISTINCT CASE WHEN Status = 'Canceled' THEN Flight_ID END) AS Number_of_Canceled_Flights
    FROM Flights
    WHERE Departure_Time <= CURRENT_TIMESTAMP
    GROUP BY Airplane_IDFK, Flight_Year, Flight_Month
) f_summary ON a.Airplane_ID = f_summary.Airplane_IDFK
LEFT JOIN (
    SELECT Airplane_IDFK, Flight_Year, Flight_Month, Dominant_Route
    FROM (
        SELECT 
            Airplane_IDFK,
            strftime('%Y', Departure_Time) AS Flight_Year,
            strftime('%m', Departure_Time) AS Flight_Month,
            Origin_AirportFK || ' - ' || Destination_AirportFK AS Dominant_Route,
            DENSE_RANK() OVER (PARTITION BY Airplane_IDFK, strftime('%Y', Departure_Time), strftime('%m', Departure_Time)
                               ORDER BY COUNT(DISTINCT Flight_ID) DESC) AS rn
        FROM Flights
        WHERE Status = 'Completed' AND Departure_Time <= CURRENT_TIMESTAMP
        GROUP BY Airplane_IDFK, Flight_Year, Flight_Month, Origin_AirportFK, Destination_AirportFK
    ) t
    WHERE rn = 1
) dr ON a.Airplane_ID = dr.Airplane_IDFK 
     AND f_summary.Flight_Year = dr.Flight_Year 
     AND f_summary.Flight_Month = dr.Flight_Month
ORDER BY f_summary.Flight_Year DESC, f_summary.Flight_Month DESC, a.Airplane_ID;