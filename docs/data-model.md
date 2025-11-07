# Database Schema and Data Model
**SOEN 342 - Rail Network Booking System**  
**Version:** 1.0 (Iteration 3)  
**Date:** November 7, 2025

---

## 1. Overview

This document specifies the relational database schema for persistent storage of routes, clients, trips, tickets, and reservations. The database replaces the in-memory storage used in Iterations 1-2.

### 1.1 Database Technology
- **Development:** SQLite 3.35+
- **Production:** PostgreSQL 12+ or MySQL 8+
- **ORM:** None (raw SQL for performance and transparency)

### 1.2 Design Principles
- **Normalization:** 3NF to eliminate redundancy
- **Referential Integrity:** Foreign keys with cascade constraints
- **Indexing:** Strategic indices for O(log n) lookups
- **Atomicity:** Transactions for multi-table operations
- **Auditability:** Immutable tickets, timestamped bookings

---

## 2. Entity-Relationship Diagram (ERD)

```
┌─────────────────────────────────────────────────────────────────┐
│                        BOOKING SYSTEM                           │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   ROUTES     │
│──────────────│
│ route_id (PK)│◄─────────┐
│ dep_city     │          │
│ arr_city     │          │ (FK)
│ dep_time     │          │
│ arr_time     │      ┌───┴─────────┐
│ train_type   │      │  TRIP_LEGS  │
│ days_op      │      │─────────────│
│ first_rate   │      │ trip_leg_id │
│ second_rate  │      │ trip_id (FK)│
└──────────────┘      │ route_id(FK)│
                      │ leg_order   │
                      └───┬─────────┘
                          │
                          │ (FK)
                          │
┌──────────────┐      ┌───▼─────────┐      ┌──────────────┐
│   CLIENTS    │      │    TRIPS    │      │   TICKETS    │
│──────────────│      │─────────────│      │──────────────│
│ client_id(PK)│      │ trip_id (PK)│◄─────┤ ticket_id(PK)│
│ first_name   │      │ book_ts     │      │ client_id(FK)│
│ last_name    │◄─────┤ dep_city    │      │ trip_id (FK) │
│ id_number    │ (FK) │ arr_city    │      │ issue_ts     │
│ age          │      │ dep_time    │      └──────────────┘
│              │      │ arr_time    │
│ UNIQUE       │      └─────────────┘
│ (last_name,  │
│  id_number)  │
└──────────────┘

Legend:
  (PK) = Primary Key
  (FK) = Foreign Key
  ◄─── = One-to-Many relationship
```

---

## 3. Table Specifications

### 3.1 `routes` - Train Route Catalog

Stores all direct train routes loaded from CSV. This is the foundation for connection searches.

```sql
CREATE TABLE routes (
    route_id TEXT PRIMARY KEY,
    departure_city TEXT NOT NULL,
    arrival_city TEXT NOT NULL,
    departure_time TEXT NOT NULL,      -- Format: "HH:MM" or "HH:MM(+Nd)"
    arrival_time TEXT NOT NULL,        -- Format: "HH:MM" or "HH:MM(+Nd)"
    train_type TEXT,                   -- e.g., "ICE", "TGV", "Regional"
    days_of_operation TEXT,            -- e.g., "Mon,Wed,Fri"
    first_class_rate REAL NOT NULL DEFAULT 0.0,
    second_class_rate REAL NOT NULL DEFAULT 0.0
);

-- Indices for fast search
CREATE INDEX idx_routes_departure ON routes(departure_city);
CREATE INDEX idx_routes_arrival ON routes(arrival_city);
CREATE INDEX idx_routes_train_type ON routes(train_type);
```

**Constraints:**
- `route_id` must be unique (primary key)
- `first_class_rate`, `second_class_rate` ≥ 0 (enforced at application layer)
- Departure/arrival cities non-empty

**Sample Data:**
| route_id | departure_city | arrival_city | departure_time | arrival_time | train_type | days_of_operation | first_class_rate | second_class_rate |
|----------|----------------|--------------|----------------|--------------|------------|-------------------|------------------|-------------------|
| R001 | Paris | Berlin | 08:30 | 16:45 | ICE | Mon,Wed,Fri | 150.00 | 89.00 |
| R002 | Berlin | Prague | 18:00 | 22:30 | EC | Daily | 75.00 | 45.00 |

**Business Rules:**
- BR-001: Route IDs immutable after creation
- BR-002: Times stored in 24-hour format
- BR-003: City names stored in title case

---

### 3.2 `clients` - Customer Registry

Stores unique client identities. Clients are deduplicated by (last_name, id_number).

```sql
CREATE TABLE clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    id_number TEXT NOT NULL,
    age INTEGER NOT NULL CHECK(age >= 0),
    UNIQUE(last_name, id_number)       -- Natural key
);

-- Index for trip lookup
CREATE INDEX idx_clients_lookup ON clients(last_name, id_number);
```

**Constraints:**
- `(last_name, id_number)` unique across all clients
- `age` ≥ 0
- Names non-empty (enforced at application layer)

**Sample Data:**
| client_id | first_name | last_name | id_number | age |
|-----------|------------|-----------|-----------|-----|
| 1 | John | Smith | PASS001 | 45 |
| 2 | Jane | Smith | PASS002 | 42 |
| 3 | Alice | Johnson | ID789 | 28 |

**Business Rules:**
- BR-015: Client identity determined by (last_name, id_number)
- BR-022: Last name matching case-insensitive (normalized to lowercase in queries)
- BR-023: ID number matching case-sensitive

---

### 3.3 `trips` - Booked Journeys

Stores high-level trip information. Each trip represents one booked connection with 1..N travelers.

```sql
CREATE TABLE trips (
    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_timestamp TEXT NOT NULL,    -- ISO8601: "YYYY-MM-DD HH:MM:SS"
    departure_city TEXT NOT NULL,
    arrival_city TEXT NOT NULL,
    departure_time TEXT NOT NULL,
    arrival_time TEXT NOT NULL
);

-- Index for date-based filtering
CREATE INDEX idx_trips_booking ON trips(booking_timestamp);
```

**Constraints:**
- `trip_id` auto-increments starting at 1
- `booking_timestamp` in ISO8601 format

**Sample Data:**
| trip_id | booking_timestamp | departure_city | arrival_city | departure_time | arrival_time |
|---------|-------------------|----------------|--------------|----------------|--------------|
| 12345 | 2025-11-07 14:30:00 | Paris | Berlin | 08:30 | 16:45 |
| 12346 | 2025-11-07 15:22:00 | Amsterdam | Brussels | 10:15 | 12:30 |

**Business Rules:**
- **BR-014 (Changed):** Trip IDs numeric (was alphanumeric in Iteration 2)
- BR-024: Trip IDs never reused (auto-increment never resets)
- BR-025: Booking timestamp immutable after creation

---

### 3.4 `trip_legs` - Route Segments of Trips

Stores the sequence of routes comprising a trip. A direct trip has 1 leg; 1-stop has 2 legs; 2-stop has 3 legs.

```sql
CREATE TABLE trip_legs (
    trip_leg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL,
    route_id TEXT NOT NULL,
    leg_order INTEGER NOT NULL,        -- 0-indexed: first leg = 0
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE,
    FOREIGN KEY (route_id) REFERENCES routes(route_id),
    UNIQUE(trip_id, leg_order)         -- One route per order position
);

-- Index for trip reconstruction
CREATE INDEX idx_trip_legs_trip ON trip_legs(trip_id, leg_order);
```

**Constraints:**
- `trip_id` references `trips.trip_id` (cascade delete)
- `route_id` references `routes.route_id`
- `(trip_id, leg_order)` unique

**Sample Data:**
| trip_leg_id | trip_id | route_id | leg_order |
|-------------|---------|----------|-----------|
| 1 | 12345 | R001 | 0 |
| 2 | 12346 | R010 | 0 |
| 3 | 12346 | R011 | 1 |

**Business Rules:**
- BR-026: Leg order must be sequential (0, 1, 2)
- BR-027: Gaps in leg_order invalid
- BR-028: Maximum 3 legs per trip (0-stop to 2-stop)

---

### 3.5 `tickets` - Individual Reservations

Stores one ticket per traveler. Multiple tickets may share the same trip (group booking).

```sql
CREATE TABLE tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    trip_id INTEGER NOT NULL,
    issue_timestamp TEXT NOT NULL,     -- ISO8601
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE
);

-- Indices for lookups
CREATE INDEX idx_tickets_client ON tickets(client_id);
CREATE INDEX idx_tickets_trip ON tickets(trip_id);
```

**Constraints:**
- `client_id` references `clients.client_id`
- `trip_id` references `trips.trip_id` (cascade delete)
- Ticket IDs never reused

**Sample Data:**
| ticket_id | client_id | trip_id | issue_timestamp |
|-----------|-----------|---------|-----------------|
| 1001 | 1 | 12345 | 2025-11-07 14:30:05 |
| 1002 | 2 | 12345 | 2025-11-07 14:30:05 |
| 1003 | 3 | 12346 | 2025-11-07 15:22:10 |

**Business Rules:**
- BR-013: Ticket IDs never reused (audit trail)
- BR-016: Tickets immutable after creation (no UPDATEs allowed)
- **BR-029:** Duplicate booking check: (client_id, trip connection) must be unique
  - Enforced at application layer by comparing route sequences

---

## 4. Relationships

### 4.1 One-to-Many Relationships

| Parent | Child | Relationship | Delete Rule |
|--------|-------|--------------|-------------|
| `routes` | `trip_legs` | One route used by many trip legs | RESTRICT (don't delete routes in use) |
| `trips` | `trip_legs` | One trip has many legs (1-3) | CASCADE (delete legs with trip) |
| `trips` | `tickets` | One trip has many tickets | CASCADE (delete tickets with trip) |
| `clients` | `tickets` | One client has many tickets | RESTRICT (don't delete clients with bookings) |

### 4.2 Many-to-Many Relationships

| Entity A | Junction Table | Entity B | Notes |
|----------|----------------|----------|-------|
| `clients` | `tickets` | `trips` | Clients linked to trips via tickets |

---

## 5. Queries and Performance

### 5.1 Critical Queries

#### Q1: Load Routes from CSV
```sql
INSERT INTO routes (route_id, departure_city, ...) 
VALUES (?, ?, ...);
```
- **Frequency:** Once at startup
- **Volume:** 1,000-50,000 rows
- **Optimization:** Batch insert in transaction

#### Q2: Search Direct Routes
```sql
SELECT * FROM routes
WHERE departure_city = ? AND arrival_city = ?
  AND (train_type = ? OR ? IS NULL)
  AND (days_of_operation LIKE ? OR ? IS NULL);
```
- **Frequency:** Hundreds per minute
- **Optimization:** Index on `departure_city`, `arrival_city`, `train_type`
- **Expected Time:** < 10ms

#### Q3: Find Client by Credentials
```sql
SELECT client_id FROM clients
WHERE LOWER(last_name) = LOWER(?) AND id_number = ?;
```
- **Frequency:** Every booking, every trip view
- **Optimization:** Index on `(last_name, id_number)`
- **Expected Time:** < 5ms

#### Q4: Get Trips for Client
```sql
SELECT t.* FROM trips t
JOIN tickets tk ON t.trip_id = tk.trip_id
WHERE tk.client_id = ?
ORDER BY t.booking_timestamp DESC;
```
- **Frequency:** Daily per active user
- **Optimization:** Index on `tickets.client_id`
- **Expected Time:** < 50ms for 1000 trips

#### Q5: Reconstruct Trip Connection
```sql
SELECT r.* FROM routes r
JOIN trip_legs tl ON r.route_id = tl.route_id
WHERE tl.trip_id = ?
ORDER BY tl.leg_order ASC;
```
- **Frequency:** Every trip view
- **Optimization:** Index on `(trip_id, leg_order)`
- **Expected Time:** < 10ms

#### Q6: Check Duplicate Booking
```sql
-- Application-level query (complex connection comparison)
-- 1. Get all trips for client
-- 2. For each trip, get trip_legs
-- 3. Compare route sequences
```
- **Frequency:** Every booking attempt
- **Optimization:** Client trips index + in-memory comparison
- **Expected Time:** < 20ms

### 5.2 Index Strategy

| Table | Index | Purpose | Impact |
|-------|-------|---------|--------|
| `routes` | `departure_city` | Search by origin | 100x faster search |
| `routes` | `arrival_city` | Search by destination | 100x faster search |
| `routes` | `train_type` | Filter by type | 50x faster filter |
| `clients` | `(last_name, id_number)` | Client lookup | O(log n) vs O(n) |
| `trip_legs` | `(trip_id, leg_order)` | Reconstruct itinerary | Critical for display |
| `tickets` | `client_id` | Find client trips | O(log n) lookup |
| `tickets` | `trip_id` | Find trip travelers | Fast manifest |

**Trade-offs:**
- **Write penalty:** Each index adds ~10% to INSERT time
- **Storage:** Indices consume 20-30% additional disk space
- **Benefit:** Query speedup of 50-1000x

---

## 6. Data Integrity

### 6.1 Constraints Summary

| Constraint Type | Count | Examples |
|----------------|-------|----------|
| Primary Keys | 5 | All tables |
| Foreign Keys | 4 | `trip_legs.trip_id`, `tickets.client_id`, etc. |
| Unique Constraints | 2 | `clients(last_name, id_number)`, `trip_legs(trip_id, leg_order)` |
| Check Constraints | 1 | `clients.age >= 0` |
| NOT NULL | 23 | All required fields |

### 6.2 Referential Integrity Rules

**Cascade Delete:**
- Deleting a trip → deletes all trip_legs and tickets for that trip
- Rationale: Trip is parent entity; children meaningless without parent

**Restrict Delete:**
- Cannot delete route if used by any trip_legs
- Cannot delete client if has any tickets
- Rationale: Historical data preservation

### 6.3 Application-Level Constraints

Some business rules enforced in Python code (not DB constraints):

- **BR-011:** One client, one reservation per connection
  - Too complex for SQL constraint (requires route sequence comparison)
  - Checked in `BookingSystem.book_trip()`

- **BR-008:** Layover validation
  - Time-based logic not suitable for DB constraint
  - Checked in `layover_validator.py`

---

## 7. Migration Strategy

### 7.1 From In-Memory to Database

**Phase 1: Schema Creation**
```python
# database.py
def init_schema(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS routes (...)")
    conn.execute("CREATE TABLE IF NOT EXISTS clients (...)")
    # ... etc
```

**Phase 2: Data Migration**
- Routes: Reload from CSV (no existing data to migrate)
- Clients, Trips, Tickets: Start fresh (Iteration 3 clean slate)

**Phase 3: Code Refactor**
- Replace `BookingSystem.trips: Dict` with SQL queries
- Replace `BookingSystem.client_trips_index: Dict` with DB index
- Update ID generation: use `cursor.lastrowid` instead of `secrets`

### 7.2 Testing Strategy

**Unit Tests:**
- Test each table CRUD operation in isolation
- Use in-memory DB (`:memory:`) for speed

**Integration Tests:**
- Test booking flow end-to-end with real DB
- Verify cascade deletes work correctly
- Test concurrent bookings (threading)

**Data Validation:**
- Compare results with Iteration 2 in-memory version
- Verify ID uniqueness across restarts

---

## 8. Database Operations Checklist

### 8.1 Initialization
```sql
-- Enable foreign keys (SQLite)
PRAGMA foreign_keys = ON;

-- Enable WAL mode for concurrency (SQLite)
PRAGMA journal_mode = WAL;

-- Set busy timeout (SQLite)
PRAGMA busy_timeout = 5000;
```

### 8.2 Backup Strategy
- **Development:** Copy `.db` file daily
- **Production:** 
  - Continuous WAL archiving (PostgreSQL)
  - Daily full backups
  - Point-in-time recovery capability

### 8.3 Monitoring
- Track query execution times
- Alert if transaction rollback rate > 5%
- Monitor DB file size growth

---

## 9. Future Enhancements

### 9.1 Additional Tables (Out of Scope)

**`payments`**
- Link tickets to payment transactions
- Support refunds, partial payments

**`seats`**
- Track seat availability per route
- Assign specific seats to tickets

**`audit_log`**
- Log all trip modifications
- Support GDPR compliance (data deletion tracking)

### 9.2 Schema Optimizations

**Partitioning:**
- Partition `trips` by booking year for faster historical queries

**Materialized Views:**
- Cache client trip counts for dashboard

**Full-Text Search:**
- Index city names for autocomplete

---

## 10. Compliance and Security

### 10.1 Data Privacy (GDPR)
- `clients` table contains PII (names, ID numbers)
- Must support data deletion ("right to be forgotten")
- Implement anonymization for historical trips

### 10.2 SQL Injection Prevention
- All queries use parameterized statements
- No string concatenation for SQL
- Example:
  ```python
  # SAFE
  cursor.execute("SELECT * FROM routes WHERE route_id = ?", (route_id,))
  
  # UNSAFE - NEVER DO THIS
  cursor.execute(f"SELECT * FROM routes WHERE route_id = '{route_id}'")
  ```

### 10.3 Access Control
- Database credentials stored in environment variables
- Separate read-only user for reporting
- Write access restricted to booking service

---

## Document Metadata

**Schema Version:** 1.0  
**Last Updated:** November 7, 2025  
**Next Review:** Before Iteration 4 (if applicable)  
**Database Files:**
- Development: `booking.db` (SQLite)
- Test: `:memory:` (in-memory SQLite)
- Production: TBD (PostgreSQL connection string)

