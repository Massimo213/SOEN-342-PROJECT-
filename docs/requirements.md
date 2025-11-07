# Requirements Specification
**SOEN 342 - Rail Network Booking System**  
**Version:** 1.3  
**Date:** November 7, 2025  
**Authors:** SOEN 342 Team

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional and non-functional requirements for the Rail Network Booking System, a software application that enables clients to search, book, and manage train travel across a European rail network.

### 1.2 Scope
The system supports:
- Route catalog management from CSV data sources
- Multi-criteria connection search (direct, 1-stop, 2-stop)
- Multi-traveler trip booking
- Trip history viewing
- Persistent data storage via relational database

### 1.3 Definitions
- **Client**: A person using the system to search or book travel
- **Route**: A direct train service between two cities
- **Connection**: A travel option (direct or with transfers)
- **Trip**: A booked journey for one or more travelers
- **Ticket**: A reservation document for one traveler
- **Layover**: Wait time between connecting trains

---

## 2. Functional Requirements

### FR-001: Load Route Catalog
**Priority:** Critical  
**Iteration:** 1  

**Description:** The system SHALL load train routes from a CSV file and maintain them in a searchable catalog.

**Inputs:**
- CSV file path containing route data (Route ID, departure city, arrival city, times, train type, days of operation, pricing)

**Processing:**
- Parse CSV with error handling
- Validate required fields
- Index routes by departure city for O(1) lookup
- Store in database (Iteration 3)

**Outputs:**
- Populated route catalog
- Count of loaded routes
- Error messages for invalid records

**Business Rules:**
- Route IDs must be unique
- Times must be in HH:MM format (with optional +Nd offset)
- Pricing must be non-negative

**Acceptance Criteria:**
- ✅ System loads 1000+ routes in < 5 seconds
- ✅ Duplicate route IDs are rejected
- ✅ Invalid time formats are logged but don't halt import

**Traceability:** Implemented in `RailNetwork.from_csv()`, `database.py` (Iteration 3)

---

### FR-002: Search Direct Connections
**Priority:** Critical  
**Iteration:** 1

**Description:** The system SHALL find direct routes matching client search criteria.

**Inputs:**
- Departure city (optional)
- Arrival city (optional)
- Train type (optional)
- Day of operation (optional)
- Travel class (first/second)

**Processing:**
- Filter routes by all specified criteria (case-insensitive)
- Calculate total price based on travel class
- Sort results by duration or price

**Outputs:**
- List of matching itineraries
- Each result includes: origin, destination, departure time, arrival time, duration, price

**Business Rules:**
- If no criteria specified, return all routes
- Empty result set is valid (no matches)

**Acceptance Criteria:**
- ✅ Partial city name matching works (e.g., "Par" matches "Paris")
- ✅ Day filtering supports comma-separated values (e.g., "Mon,Wed,Fri")
- ✅ Results sorted by duration ascending by default

**Traceability:** Implemented in `RailNetwork.search()`

---

### FR-003: Search Multi-Stop Connections
**Priority:** High  
**Iteration:** 1

**Description:** The system SHALL compute indirect connections with up to 2 transfers.

**Inputs:**
- Same as FR-002
- max_stops: 0 (direct), 1, or 2
- min_transfer_minutes: minimum layover time

**Processing:**
- Generate 1-stop connections: Route A → Route B (where A.arrival_city = B.departure_city)
- Generate 2-stop connections: A → B → C
- Validate transfer feasibility (arrival time < departure time with minimum gap)
- Deduplicate identical route sequences

**Outputs:**
- Combined list of direct, 1-stop, 2-stop connections
- Each result includes transfer time breakdown

**Business Rules:**
- Transfer time must be ≥ min_transfer_minutes
- Cannot transfer to same route ID
- Multi-day offsets handled via (+Nd) notation

**Acceptance Criteria:**
- ✅ No duplicate connections in results
- ✅ Transfer times correctly calculated across day boundaries
- ✅ 2-stop search completes in < 10 seconds for 1000 routes

**Traceability:** Implemented in `RailNetwork._build_one_stop()`, `_build_two_stops()`

---

### FR-004: Validate Layover Durations (NEW - Iteration 3)
**Priority:** High  
**Iteration:** 3

**Description:** The system SHALL enforce time-based layover policies to avoid unreasonable connection times.

**Inputs:**
- Arrival time at transfer station (minutes since midnight)
- Departure time of connecting train (minutes since midnight)

**Processing:**
- Determine if layover occurs during day hours (06:00-22:00) or after hours
- Apply policy rules:
  - **Daytime**: 15-120 minutes acceptable
  - **After hours**: 15-30 minutes acceptable
- Reject connections outside acceptable ranges

**Outputs:**
- Boolean: connection valid/invalid
- Rejection reason (if invalid)

**Business Rules:**
- Policy configurable via system parameter
- Hour boundaries: day=06:00-22:00, night=22:00-06:00
- Applies to all connections, not just searches

**Acceptance Criteria:**
- ✅ 3-hour daytime layover rejected
- ✅ 45-minute after-hours layover rejected
- ✅ 90-minute daytime layover accepted
- ✅ Policy can be toggled between "strict" and "lenient"

**Traceability:** Implemented in `layover_validator.py`, integrated into `RailNetwork._transfer_gap_ok()`

---

### FR-005: Book Trip for Single Traveler
**Priority:** Critical  
**Iteration:** 2

**Description:** The system SHALL allow a client to book a selected connection for one traveler.

**Inputs:**
- Selected connection (Itinerary object)
- Traveler details: first name, last name, ID number, age

**Processing:**
- Validate traveler data (non-empty names, valid age)
- Check no existing reservation for this client on this connection
- Generate unique ticket ID (numeric)
- Generate unique trip ID (alphanumeric Iteration 2, numeric Iteration 3)
- Create reservation linking client, ticket, and trip
- Persist to database (Iteration 3)

**Outputs:**
- Trip object with trip ID
- Ticket object with ticket ID
- Confirmation message

**Business Rules:**
- One client can only have one reservation per specific connection
- Age must be ≥ 0
- ID number uniquely identifies client (along with last name)

**Acceptance Criteria:**
- ✅ Trip ID unique across all bookings
- ✅ Ticket ID unique across all tickets
- ✅ Duplicate booking rejected with clear error
- ✅ Transaction atomic (all-or-nothing)

**Traceability:** Implemented in `BookingSystem.book_trip()`

---

### FR-006: Book Trip for Multiple Travelers
**Priority:** High  
**Iteration:** 2

**Description:** The system SHALL support group bookings for the same connection.

**Inputs:**
- Selected connection
- List of travelers (1 to N): each with first name, last name, ID number, age

**Processing:**
- Validate no duplicate travelers in single booking
- Check each traveler doesn't have existing reservation for this connection
- Generate unique ticket for each traveler
- Link all tickets to single trip
- Persist to database (Iteration 3)

**Outputs:**
- Trip object containing N reservations
- N ticket objects
- Confirmation with total travelers

**Business Rules:**
- All travelers must be for the same connection
- No duplicate clients within single trip
- Each traveler gets separate ticket but shares trip ID

**Acceptance Criteria:**
- ✅ Family of 4 booked successfully
- ✅ Duplicate traveler in same booking rejected
- ✅ Each ticket has unique ID
- ✅ All reservations reference same connection

**Traceability:** Implemented in `BookingSystem.book_trip()` (multi-traveler flow)

---

### FR-007: View Current Trips
**Priority:** High  
**Iteration:** 2

**Description:** The system SHALL display all future/current trips for a client.

**Inputs:**
- Client last name (case-insensitive)
- Client ID number

**Processing:**
- Lookup trips by (last_name, id_number) key
- Filter for trips where departure >= today
- Sort by booking timestamp (most recent first)

**Outputs:**
- List of current trips with:
  - Trip ID
  - Connection details (origin, destination, times)
  - Number of travelers
  - Booking date

**Business Rules:**
- "Current" means today or future departure
- Empty list valid if no matches

**Acceptance Criteria:**
- ✅ Lookup completes in O(1) time via index
- ✅ Case-insensitive last name matching
- ✅ Shows trips across all connections

**Traceability:** Implemented in `BookingSystem.get_trips_by_client()`

---

### FR-008: View Trip History
**Priority:** Medium  
**Iteration:** 2

**Description:** The system SHALL display past trips for a client.

**Inputs:**
- Client last name
- Client ID number

**Processing:**
- Lookup trips by (last_name, id_number)
- Filter for trips where departure < today
- Sort by booking timestamp (most recent first)

**Outputs:**
- List of past trips (same format as FR-007)

**Business Rules:**
- "Past" means departure before today
- Historical data retained indefinitely (archival in future iterations)

**Acceptance Criteria:**
- ✅ Past trips separated from current
- ✅ History includes all completed journeys
- ✅ Sorted chronologically

**Traceability:** Implemented in `BookingSystem.get_trips_by_client()` (past_trips return value)

---

### FR-009: Generate Unique Trip IDs (MODIFIED - Iteration 3)
**Priority:** Critical  
**Iteration:** 3

**Description:** The system SHALL assign a unique numerical ID to each booked trip.

**Inputs:**
- (Internal) Trip creation event

**Processing:**
- Use database auto-increment for trip_id (INTEGER PRIMARY KEY)
- Guarantee uniqueness via database constraint
- Return ID immediately after trip creation

**Outputs:**
- Numeric trip ID (e.g., 12345)

**Business Rules:**
- IDs sequential but not necessarily consecutive (if deletions occur)
- IDs never reused
- IDs start at 1

**Acceptance Criteria:**
- ✅ Changed from alphanumeric (TRP-XXX) to numeric
- ✅ 1 million trips → IDs fit in 32-bit integer
- ✅ No collisions possible

**Traceability:** Implemented in database schema `trips.trip_id`, `BookingSystem.book_trip()`

---

### FR-010: Generate Unique Ticket IDs
**Priority:** Critical  
**Iteration:** 2

**Description:** The system SHALL assign a unique numerical ID to each ticket.

**Inputs:**
- (Internal) Ticket creation event

**Processing:**
- Use database auto-increment for ticket_id (INTEGER PRIMARY KEY)
- Guarantee uniqueness via database constraint

**Outputs:**
- Numeric ticket ID (e.g., 173012345678901)

**Business Rules:**
- IDs sortable by issue time
- IDs never reused

**Acceptance Criteria:**
- ✅ 64-bit integer capacity (9.2 quintillion tickets)
- ✅ No collisions
- ✅ Monotonically increasing

**Traceability:** Implemented in database schema `tickets.ticket_id`

---

## 3. Non-Functional Requirements

### NFR-001: Database Persistence (NEW - Iteration 3)
**Priority:** Critical  
**Iteration:** 3

**Description:** The system SHALL persist all data using a relational database.

**Requirements:**
- Use SQLite (development) or PostgreSQL/MySQL (production)
- ACID compliance for booking transactions
- Foreign key constraints enforced
- Schema versioning via migration scripts

**Rationale:** In-memory storage loses data on restart; production systems require durability.

**Acceptance Criteria:**
- ✅ Data survives application restart
- ✅ Concurrent bookings handled safely
- ✅ Referential integrity maintained
- ✅ Schema documented in ERD

**Metrics:**
- Booking transaction latency < 100ms (SQLite)
- Supports 1000+ concurrent connections (PostgreSQL)

**Traceability:** Implemented in `database.py`, migration from in-memory to DB in `BookingSystem`

---

### NFR-002: Performance - Search Response Time
**Priority:** High  
**Iteration:** 1

**Description:** Connection searches SHALL complete within acceptable time limits.

**Requirements:**
- Direct search: < 500ms for 10,000 routes
- 1-stop search: < 2s for 10,000 routes
- 2-stop search: < 10s for 10,000 routes

**Rationale:** User experience degrades significantly beyond 10s wait.

**Acceptance Criteria:**
- ✅ Measured via `time` command
- ✅ Includes CSV parsing + search
- ✅ Tests run on standard laptop (2GHz CPU, 8GB RAM)

**Traceability:** Addressed via indexing in `RailNetwork`

---

### NFR-003: Scalability
**Priority:** Medium  
**Iteration:** 1-3

**Description:** The system SHALL handle expected data volumes efficiently.

**Requirements:**
- Support 50,000+ routes
- Support 100,000+ trips
- Support 500,000+ tickets
- Memory usage < 2GB for full dataset

**Acceptance Criteria:**
- ✅ Database indices maintain O(log n) lookup
- ✅ No memory leaks over 24-hour operation
- ✅ Pagination for large result sets

**Traceability:** Database indexing, query optimization

---

### NFR-004: Data Integrity
**Priority:** Critical  
**Iteration:** 2-3

**Description:** The system SHALL maintain data consistency at all times.

**Requirements:**
- No orphaned tickets (ticket without trip)
- No duplicate bookings for same client-connection
- Client identity uniquely determined by (last_name, id_number)
- Immutable tickets (audit trail)

**Acceptance Criteria:**
- ✅ Foreign key constraints prevent orphans
- ✅ UNIQUE constraints prevent duplicates
- ✅ Ticket records never updated after creation
- ✅ All bookings logged with timestamp

**Traceability:** Database constraints, immutable dataclasses in domain model

---

### NFR-005: Usability
**Priority:** Medium  
**Iteration:** 1-2

**Description:** The system SHALL provide clear, user-friendly interfaces.

**Requirements:**
- CLI prompts guide user through booking flow
- Error messages explain validation failures
- Results formatted in readable tables
- Help text available via `--help`

**Acceptance Criteria:**
- ✅ Non-technical user can book trip without documentation
- ✅ Error messages include corrective actions
- ✅ Results include units (minutes, euros)

**Traceability:** Implemented in `booking_cli.py`, error handling throughout

---

### NFR-006: Maintainability
**Priority:** High  
**Iteration:** 1-3

**Description:** The system SHALL be maintainable by other developers.

**Requirements:**
- Code follows PEP 8 style guide
- Functions documented with docstrings
- Architecture documented with diagrams
- Design decisions explained in post-mortems
- Comprehensive test coverage (>80%)

**Acceptance Criteria:**
- ✅ New developer can understand codebase in < 2 hours
- ✅ UML diagrams match implementation
- ✅ All public APIs documented

**Traceability:** README.md, docs/, inline comments, test coverage

---

### NFR-007: Testability
**Priority:** High  
**Iteration:** 1-3

**Description:** The system SHALL be thoroughly testable.

**Requirements:**
- Unit tests for all domain logic
- Integration tests for booking flows
- Database tests use in-memory SQLite
- Tests runnable without external dependencies

**Acceptance Criteria:**
- ✅ `python test_booking.py` runs all tests
- ✅ Tests complete in < 30 seconds
- ✅ Clear pass/fail output

**Traceability:** Implemented in `test_booking.py`

---

## 4. Requirements Traceability Matrix

| Requirement | Use Case | Module | Test |
|-------------|----------|--------|------|
| FR-001 | Load Records | `rail_network.py`, `database.py` | `test_load_routes()` |
| FR-002 | Search Connections | `rail_network.py` | `test_direct_search()` |
| FR-003 | Search Connections | `rail_network.py` | `test_multistop_search()` |
| FR-004 | Search Connections | `layover_validator.py` | `test_layover_policy()` |
| FR-005 | Book Trip | `booking_system.py` | `test_solo_booking()` |
| FR-006 | Book Trip | `booking_system.py` | `test_family_booking()` |
| FR-007 | View Trips | `booking_system.py` | `test_view_current_trips()` |
| FR-008 | View Trips | `booking_system.py` | `test_view_past_trips()` |
| FR-009 | Book Trip | `database.py`, `booking_system.py` | `test_numeric_trip_id()` |
| FR-010 | Book Trip | `database.py`, `booking_system.py` | `test_unique_ticket_ids()` |
| NFR-001 | All | `database.py` | `test_persistence()` |
| NFR-002 | Search Connections | `rail_network.py` | `test_search_performance()` |
| NFR-004 | Book Trip | `booking_system.py`, DB schema | `test_duplicate_prevention()` |
| NFR-007 | All | `test_booking.py` | All tests |

---

## 5. Constraints

### 5.1 Technical Constraints
- Python 3.8+ required
- SQLite 3.35+ or PostgreSQL 12+
- CSV data format defined by `eu_rail_network.csv` structure
- No external API dependencies

### 5.2 Business Constraints
- System operates in single currency (EUR)
- Time zone handling out of scope (assumes all times in CET)
- No real-time seat availability (future work)
- No payment processing (booking only)

---

## 6. Assumptions and Dependencies

### 6.1 Assumptions
- Route data is accurate and maintained by external process
- Client ID numbers are unique and valid
- Users have basic command-line proficiency
- System runs on trusted network (no authentication in current iteration)

### 6.2 Dependencies
- Python standard library only (no external packages)
- SQLite database engine (bundled with Python)
- CSV route data file

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Oct 15, 2025 | Team | Initial requirements (Iteration 1) |
| 1.1 | Oct 25, 2025 | Team | Added booking requirements (Iteration 2) |
| 1.2 | Nov 5, 2025 | Team | Added persistence requirements (Iteration 3) |
| 1.3 | Nov 7, 2025 | Team | Added layover validation, numeric trip IDs |

