# Use Case Specifications
**SOEN 342 - Rail Network Booking System**  
**Version:** 1.3  
**Date:** November 7, 2025

---

## Use Case Index

1. [UC-001: Load Route Records](#uc-001-load-route-records)
2. [UC-002: Search for Connections](#uc-002-search-for-connections)
3. [UC-003: Book a Trip](#uc-003-book-a-trip)
4. [UC-004: View Trips](#uc-004-view-trips)

---

## UC-001: Load Route Records

### Brief Description
The system administrator loads train route data from a CSV file into the system's route catalog, making it available for client searches and bookings.

### Actors
- **Primary:** System Administrator
- **Secondary:** Database

### Preconditions
- System is running and has write access to database
- CSV file exists at specified path
- CSV contains properly formatted route data
- Database schema is initialized

### Postconditions
**Success:**
- All valid routes stored in database
- Routes indexed by departure city for fast lookup
- Route count displayed to administrator
- System ready for client searches

**Failure:**
- Error log created with invalid records
- Partial import possible if some records valid
- System state unchanged if critical error

### Main Success Scenario
1. Administrator starts system or invokes load command with CSV file path
2. System opens CSV file and reads header row
3. System validates header contains required columns:
   - Route ID
   - Departure City, Arrival City
   - Departure Time, Arrival Time
   - Train Type
   - Days of Operation
   - First Class Rate, Second Class Rate
4. For each data row:
   - System parses route fields
   - System validates data format (times, numeric rates)
   - System checks route ID uniqueness
   - System inserts route into `routes` table
   - System updates departure city index
5. System commits database transaction
6. System displays: "Loaded {count} routes successfully"
7. Use case ends

### Extensions (Alternate Flows)

**3a. Required column missing:**
1. System logs error: "Invalid CSV format - missing column: {column_name}"
2. System aborts load operation
3. Use case ends in failure

**4a. Invalid time format in row:**
1. System logs warning: "Row {n}: Invalid time format '{value}'"
2. System skips row and continues with next
3. Continue from step 4

**4b. Duplicate route ID:**
1. System logs error: "Row {n}: Duplicate route ID '{route_id}'"
2. System skips row (keeps first occurrence)
3. Continue from step 4

**4c. Negative pricing:**
1. System logs warning: "Row {n}: Negative price, setting to 0"
2. System corrects price to 0
3. Continue with row processing at step 4

**5a. Database transaction fails:**
1. System rolls back all changes
2. System logs error: "Database error: {error_message}"
3. System displays: "Route load failed - no changes made"
4. Use case ends in failure

### Special Requirements
- **Performance:** Load 10,000 routes in < 30 seconds
- **Memory:** Process CSV in streaming mode if > 100MB
- **Logging:** All errors/warnings written to log file

### Frequency of Occurrence
- Once at system startup
- On-demand when route data updated (weekly/monthly)

### Business Rules
- BR-001: Route IDs must be unique within system
- BR-002: Departure time must be before arrival time (accounting for day offsets)
- BR-003: Pricing must be non-negative
- BR-004: City names normalized to title case
- BR-005: Times stored in HH:MM format with optional (+Nd) offset

### Notes and Issues
- **Issue:** CSV may contain stray whitespace - system trims all fields
- **Issue:** Time zone handling not implemented - assumes all times in CET
- **Future:** Support multiple CSV formats via configuration

---

## UC-002: Search for Connections

### Brief Description
A client searches for train connections between two cities, optionally filtering by train type, day of week, and number of stops. The system returns matching connections sorted by duration or price.

### Actors
- **Primary:** Client
- **Secondary:** Route Catalog (Database)

### Preconditions
- Routes have been loaded (UC-001 completed)
- System is responsive
- Client has access to CLI or API

### Postconditions
**Success:**
- Client receives list of connections matching criteria
- Connections include direct routes and valid multi-stop options
- Results sorted by client preference (duration or price)
- All layover times comply with system policy (Iteration 3)

**Failure:**
- Client receives empty result set if no matches
- Client receives error message if invalid criteria provided

### Main Success Scenario
1. Client enters search criteria:
   - Departure city (required for multi-stop)
   - Arrival city (required for multi-stop)
   - Train type (optional)
   - Day of operation (optional)
   - Maximum stops (0, 1, or 2)
   - Minimum transfer time (default: 15 minutes)
   - Travel class (first or second)
   - Sort preference (duration or price)
2. System validates input:
   - Cities exist in catalog
   - Day format valid (e.g., "Mon", "Monday", or "Mon,Wed")
   - Max stops in valid range
3. System searches direct routes matching criteria
4. System adds direct routes to result set
5. If max_stops ≥ 1:
   - System computes 1-stop connections
   - System validates transfer times meet minimum requirement
   - **[Iteration 3]** System applies layover policy validation
   - System adds valid 1-stop connections to result set
6. If max_stops = 2:
   - System computes 2-stop connections
   - System validates all transfer times
   - **[Iteration 3]** System applies layover policy to both transfers
   - System adds valid 2-stop connections to result set
7. System deduplicates connections (same route sequence)
8. System calculates total price for each connection based on travel class
9. System sorts results by specified preference
10. System displays results in table or JSON format
11. Client reviews connections
12. Use case ends

### Extensions (Alternate Flows)

**2a. Invalid city name:**
1. System displays: "No routes found for city: {city_name}"
2. System suggests similar city names if available
3. Client may retry with corrected name
4. Use case ends

**2b. Invalid day format:**
1. System displays: "Invalid day format. Use full name (Monday) or abbreviation (Mon)"
2. Use case ends

**3-6. No matches found:**
1. System displays: "No connections found matching your criteria"
2. System suggests: "Try increasing max stops or removing filters"
3. Use case ends

**5a. 1-stop connection violates layover policy (Iteration 3):**
1. System evaluates layover duration against time-of-day policy
2. If layover too short:
   - System logs: "Connection rejected: insufficient transfer time"
   - System excludes connection from results
3. If layover too long:
   - System logs: "Connection rejected: excessive layover ({duration} min)"
   - System excludes connection from results
4. Continue evaluating remaining connections

**6a. 2-stop connection has invalid transfer:**
1. Same as 5a, but applied to both transfer points
2. Connection rejected if either transfer invalid
3. Continue evaluating remaining connections

**8a. Client requests CSV export:**
1. System writes results to CSV file at specified path
2. System displays: "Wrote {count} results to {filename}"
3. Use case ends

### Special Requirements
- **Performance:** 
  - Direct search: < 500ms for 10,000 routes
  - 2-stop search: < 10s for 10,000 routes
- **Usability:** Display durations in hours:minutes format
- **Accuracy:** Transfer times must account for day rollovers

### Frequency of Occurrence
- Hundreds of times daily per user
- Peak usage during booking windows

### Business Rules
- BR-006: Direct connections preferred in sort order (tie-breaker)
- BR-007: Transfer time ≥ 15 minutes (configurable)
- **BR-008 (NEW - Iteration 3):** Layover validation policy:
  - **Daytime (06:00-22:00):** 15-120 minutes acceptable
  - **After hours (22:00-06:00):** 15-30 minutes acceptable
- BR-009: Maximum 2 stops (limitation of current algorithm)
- BR-010: Travel class affects pricing but not route selection

### Notes and Issues
- **Performance:** 2-stop search is O(R³) worst case - consider graph algorithms for scale
- **Limitation:** Day-of-operation filtering assumes same day for entire journey
- **Future:** Add departure time window filtering ("after 2pm")
- **Iteration 3:** Layover policy configurable via "strict" or "lenient" modes

---

## UC-003: Book a Trip

### Brief Description
A client selects a connection and books a trip for one or more travelers. The system generates unique trip and ticket IDs, validates no duplicate bookings exist, and persists the reservation to the database.

### Actors
- **Primary:** Client
- **Secondary:** Booking System, Database

### Preconditions
- Client has searched and selected a connection (UC-002 completed)
- Connection is valid and meets layover policies
- Database is accessible and writable
- Client has valid identification information

### Postconditions
**Success:**
- Trip created with unique numeric ID (Iteration 3)
- One ticket per traveler, each with unique numeric ID
- All tickets linked to single trip
- Trip and tickets persisted in database
- Client can retrieve booking via last name + ID

**Failure:**
- No trip created if validation fails
- Database state unchanged (transaction rollback)
- Error message explains reason for failure

### Main Success Scenario
1. Client initiates booking for selected connection
2. System displays connection summary (origin, destination, times, price)
3. System prompts: "How many travelers?"
4. Client enters number of travelers (1..N)
5. For each traveler:
   - System prompts: "Enter first name:"
   - Client enters first name
   - System prompts: "Enter last name:"
   - Client enters last name
   - System prompts: "Enter ID number (passport/state ID):"
   - Client enters ID number
   - System prompts: "Enter age:"
   - Client enters age
6. System validates all traveler data:
   - Names not empty
   - Ages ≥ 0
   - No duplicate travelers in this booking
7. System checks for duplicate bookings:
   - For each traveler, query existing trips
   - Verify no reservation exists for same client on same connection
8. System begins database transaction
9. System generates numeric trip ID via database auto-increment
10. For each traveler:
    - System inserts client record (or retrieves existing via last name + ID)
    - System generates ticket ID via database auto-increment
    - System inserts ticket record linking client and trip
    - System creates reservation object in memory
11. System inserts trip record with connection details
12. System inserts trip_legs records (one per leg of journey)
13. System commits database transaction
14. System displays:
    - "Booking successful!"
    - "Trip ID: {numeric_id}"
    - "Travelers: {count}"
    - "Total cost: {price} EUR"
    - "Tickets: {ticket_id_1}, {ticket_id_2}, ..."
15. Client notes trip ID for future reference
16. Use case ends

### Extensions (Alternate Flows)

**4a. Client enters invalid number:**
1. System displays: "Number of travelers must be positive integer"
2. Return to step 3

**5a. Client leaves field blank:**
1. System displays: "This field is required"
2. Re-prompt for same field

**6a. Age validation fails:**
1. System displays: "Age must be non-negative"
2. Re-prompt for age

**6b. Duplicate traveler in booking:**
1. System displays: "Traveler {name} ({id}) already in this booking"
2. System prompts: "Re-enter traveler {n} details"
3. Return to step 5 for that traveler

**7a. Client already has reservation for this connection:**
1. System displays:
   - "Duplicate booking detected!"
   - "Client {name} already has reservation for this connection"
   - "Existing trip ID: {trip_id}"
2. System prompts: "Do you want to view existing booking? (y/n)"
3. If yes:
   - System displays trip details
   - Client may exit or modify search
4. Use case ends

**8-13a. Database error:**
1. System catches exception
2. System rolls back transaction
3. System displays: "Booking failed: {error_reason}"
4. System logs full error trace
5. Use case ends in failure

**13a. Client requests booking cancellation (future):**
1. Not implemented in current iteration
2. System displays: "Cancellation not supported - contact administrator"

### Special Requirements
- **Performance:** Booking transaction < 100ms (SQLite)
- **Atomicity:** All-or-nothing - no partial bookings
- **Concurrency:** Handle simultaneous bookings for same connection
- **Security:** Validate all inputs against SQL injection (parameterized queries)

### Frequency of Occurrence
- Daily per active client
- Peak during holiday booking seasons

### Business Rules
- **BR-011:** One client can only have one reservation per connection
- BR-012: All travelers in single booking share same connection
- BR-013: Ticket IDs never reused (audit requirement)
- **BR-014 (CHANGED - Iteration 3):** Trip IDs numeric (was alphanumeric)
- BR-015: Client identity determined by (last_name, id_number) tuple
- BR-016: Tickets immutable after creation (no updates allowed)

### Notes and Issues
- **Change (Iteration 3):** Trip IDs changed from alphanumeric (TRP-XXXX) to numeric for database efficiency
- **Limitation:** No payment processing - booking only
- **Limitation:** No seat selection - assumes infinite capacity
- **Future:** Email confirmation with QR code ticket
- **Future:** Multi-currency support

---

## UC-004: View Trips

### Brief Description
A client retrieves their booking history by providing their last name and ID number. The system displays both current (today/future) and past trips separately, showing full details of each reservation.

### Actors
- **Primary:** Client
- **Secondary:** Booking System, Database

### Preconditions
- Client has made at least one booking (UC-003 completed)
- Client knows their registered last name and ID number
- Database is accessible

### Postconditions
**Success:**
- Client sees all their trips separated into:
  - **Current trips:** Departures today or in future
  - **Past trips:** Departures before today
- Each trip shows: ID, origin, destination, times, travelers, booking date

**Failure:**
- Client sees "No trips found" if no bookings exist
- Error message if database unavailable

### Main Success Scenario
1. Client initiates view trips command
2. System prompts: "Enter last name:"
3. Client enters last name
4. System prompts: "Enter ID number:"
5. Client enters ID number
6. System normalizes input:
   - Converts last name to lowercase for case-insensitive matching
   - Trims whitespace from ID number
7. System queries database:
   - Lookup trips via index on (last_name, id_number)
   - Retrieve all trips where client has reservation
8. System categorizes trips:
   - Compare trip departure date to today's date
   - Separate into current_trips and past_trips lists
9. System sorts each list by booking timestamp (most recent first)
10. System displays:
    - "=== CURRENT TRIPS ==="
    - For each current trip:
      - Trip ID: {id}
      - Route: {origin} → {destination}
      - Departure: {date} {time}
      - Arrival: {date} {time}
      - Travelers: {count} ({names})
      - Booked: {booking_date}
      - Tickets: {ticket_ids}
    - "=== PAST TRIPS ==="
    - Same format for each past trip
11. Client reviews trip history
12. Use case ends

### Extensions (Alternate Flows)

**7a. No trips found for client:**
1. System displays:
   - "No trips found for {last_name} (ID: {id_number})"
   - "If you recently booked, verify your details"
2. Use case ends

**7b. Database connection error:**
1. System displays: "Unable to retrieve trips - please try again later"
2. System logs error for administrator
3. Use case ends in failure

**8a. All trips are current:**
1. System displays only "CURRENT TRIPS" section
2. System displays: "(No past trips)"
3. Continue from step 11

**8b. All trips are past:**
1. System displays only "PAST TRIPS" section
2. System displays: "(No current trips)"
3. Continue from step 11

**11a. Client requests trip details:**
1. System prompts: "Enter trip ID for full details:"
2. Client enters trip ID
3. System displays expanded view:
   - Full connection details (all legs)
   - Each leg's train type, departure/arrival stations, times
   - Transfer times at each stop
   - Complete traveler manifest
   - Individual ticket numbers
4. Client may request another trip or exit

**11b. Client requests trip export:**
1. System prompts: "Export to CSV? (y/n)"
2. If yes:
   - System writes trips to CSV file
   - System displays: "Trips exported to trips_{last_name}_{id}.csv"
3. Use case ends

### Special Requirements
- **Performance:** Lookup < 500ms for 100,000 trips
- **Privacy:** No authentication in current iteration - rely on ID number secrecy
- **Usability:** Clear visual separation of current vs. past
- **Accessibility:** Text-only output readable by screen readers

### Frequency of Occurrence
- Weekly per active client
- Daily for frequent travelers

### Business Rules
- BR-017: "Current" means departure date ≥ today
- BR-018: "Past" means departure date < today
- BR-019: Trips never deleted from database (archival retention)
- BR-020: Last name matching case-insensitive
- BR-021: ID number matching case-sensitive and exact

### Data Integrity Rules
- Client must exist in trips (if no trips, client unknown to system)
- All displayed trips must have valid connection data
- Ticket counts must match traveler counts

### Notes and Issues
- **Limitation:** Date comparison simplified - actual implementation uses booking timestamp as proxy (CSV lacks full dates)
- **Security concern:** No authentication - anyone with name+ID can view trips
- **Future:** Add email/SMS-based verification
- **Future:** Allow filtering by date range, destination
- **Iteration 3:** Query optimized via database indexing on (last_name, id_number)

---

## Use Case Relationships

### Dependencies
- UC-002 (Search) depends on UC-001 (Load)
- UC-003 (Book) depends on UC-002 (Search)
- UC-004 (View) depends on UC-003 (Book)

### Extensions
- UC-003 may trigger UC-002 (client re-searches if booking fails)
- UC-004 may include UC-003 (quick re-book from history - future)

### Generalizations
None in current system

---

## Traceability to Requirements

| Use Case | Requirements Satisfied |
|----------|----------------------|
| UC-001 | FR-001 (Load catalog), NFR-001 (Persistence) |
| UC-002 | FR-002 (Direct search), FR-003 (Multi-stop), FR-004 (Layover validation), NFR-002 (Performance) |
| UC-003 | FR-005 (Solo booking), FR-006 (Group booking), FR-009 (Numeric trip ID), FR-010 (Ticket ID), NFR-001 (Persistence), NFR-004 (Integrity) |
| UC-004 | FR-007 (Current trips), FR-008 (Past trips), NFR-001 (Persistence) |

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Oct 15, 2025 | Team | Initial use cases (Iteration 1) |
| 1.1 | Oct 25, 2025 | Team | Added UC-003, UC-004 (Iteration 2) |
| 1.2 | Nov 5, 2025 | Team | Updated for database persistence (Iteration 3) |
| 1.3 | Nov 7, 2025 | Team | Added layover validation, numeric trip IDs |

