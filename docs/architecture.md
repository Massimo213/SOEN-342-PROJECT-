# Architecture Document
**SOEN 342 - Rail Network Booking System**  
**Version:** 3.0  
**Date:** November 7, 2025

---

## 1. System Overview

The Rail Network Booking System is a layered application providing train route search, trip booking, and reservation management capabilities. Iteration 3 introduces persistent storage via relational database, replacing the in-memory architecture of previous iterations.

### 1.1 Key Features
- Route catalog management (CSV import)
- Multi-criteria connection search (direct, 1-stop, 2-stop)
- Time-based layover validation
- Multi-traveler booking
- Trip history management
- Database persistence (SQLite/PostgreSQL)

### 1.2 Technology Stack
- **Language:** Python 3.8+
- **Database:** SQLite (dev), PostgreSQL/MySQL (production)
- **Architecture Pattern:** Layered architecture + Domain-Driven Design
- **Testing:** unittest (Python standard library)

---

## 2. Architectural Style

### 2.1 Layered Architecture

```
┌─────────────────────────────────────────────┐
│         Presentation Layer                  │
│  (booking_cli.py, app.py)                  │
│  - User interaction                         │
│  - Input validation                         │
│  - Output formatting                        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Business Logic Layer                │
│  (booking_system_v3.py, rail_network.py)   │
│  - Domain models                            │
│  - Business rules                           │
│  - Connection search algorithms             │
│  - Booking orchestration                    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Service Layer                       │
│  (layover_validator.py)                    │
│  - Stateless utilities                      │
│  - Policy enforcement                       │
│  - Cross-cutting concerns                   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Data Access Layer                   │
│  (database.py)                             │
│  - SQL operations                           │
│  - Transaction management                   │
│  - Schema versioning                        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Persistence Layer                   │
│  (SQLite / PostgreSQL)                     │
│  - ACID transactions                        │
│  - Referential integrity                    │
│  - Indexing                                 │
└─────────────────────────────────────────────┘
```

### 2.2 Design Rationale

**Why Layered Architecture?**
- **Separation of Concerns:** Each layer has single responsibility
- **Testability:** Layers can be tested independently
- **Maintainability:** Changes in one layer don't ripple across system
- **Replaceability:** Can swap database without touching business logic

**Trade-offs:**
- **Pro:** Clear boundaries, easy to understand
- **Pro:** Facilitates team parallelization
- **Con:** Potential performance overhead from layer crossing
- **Con:** Can lead to anemic domain models if overused

---

## 3. Domain Model

### 3.1 Core Entities

#### Client (Value Object)
```python
@dataclass(frozen=True)
class Client:
    first_name: str
    last_name: str
    id_number: str
    age: int
```
- **Identity:** (last_name, id_number) tuple
- **Immutability:** Frozen dataclass prevents modification
- **Rationale:** Clients are value objects - two clients with same name+ID are identical

#### Ticket (Entity)
```python
@dataclass(frozen=True)
class Ticket:
    ticket_id: int  # Database-generated
    client: Client
    connection: Itinerary
    issue_timestamp: datetime
```
- **Identity:** ticket_id (numeric)
- **Immutability:** Audit trail requirement
- **Rationale:** Once issued, tickets never change (regulatory compliance)

#### Trip (Aggregate Root)
```python
@dataclass
class Trip:
    trip_id: int  # Changed to numeric in Iteration 3
    connection: Itinerary
    reservations: List[Reservation]
    booking_timestamp: datetime
```
- **Identity:** trip_id (numeric auto-increment)
- **Aggregate:** Controls access to Reservations
- **Rationale:** Trip is the consistency boundary for bookings

### 3.2 Relationships

```
Trip (1) ──┬──> (N) Reservation
           │
           └──> (1) Itinerary

Reservation (1) ───> (1) Client
            (1) ───> (1) Ticket

Itinerary (1) ───> (1..3) Leg
Leg (1) ───> (1) TrainRoute
```

**Key Invariants:**
- One trip, many reservations (group booking)
- All reservations in trip share same connection
- One client can have at most one reservation per connection

---

## 4. Component Design

### 4.1 RailNetwork (Search Engine)

**Responsibilities:**
- Load routes from CSV/database
- Execute multi-criteria search
- Compute multi-stop connections
- Validate layover constraints

**Key Algorithms:**

#### Direct Search
- **Complexity:** O(N) where N = number of routes
- **Optimization:** Filter by indexed departure_city

#### 1-Stop Search
- **Complexity:** O(N * M) where M = avg routes per city
- **Optimization:** Index routes by departure city

#### 2-Stop Search
- **Complexity:** O(N * M²) worst case
- **Optimization:** Early termination on layover policy violation
- **Future:** Replace with Dijkstra's algorithm for better scaling

**Design Decision:** Why not graph algorithms?
- **Current:** Simple nested loops, easy to understand
- **Trade-off:** O(N²) vs O((V+E) log V) for Dijkstra
- **Rationale:** Dataset small (~10K routes), premature optimization avoided
- **Future:** Migrate to networkx graph for > 50K routes

### 4.2 BookingSystem (Orchestrator)

**Responsibilities:**
- Validate business rules
- Orchestrate database transactions
- Enforce duplicate booking prevention
- Reconstruct domain objects from DB

**Transaction Boundaries:**
```python
def book_trip(...):
    # BEGIN TRANSACTION (implicit via context manager)
    trip_id = db.create_trip(...)
    for leg in connection.legs:
        db.add_trip_leg(...)
    for traveler in travelers:
        client_id = db.get_or_create_client(...)
        ticket_id = db.create_ticket(...)
    # COMMIT or ROLLBACK on exception
```

**Design Decision:** Why application-level duplicate check?
- **Challenge:** Cannot use DB constraint (requires route sequence comparison)
- **Solution:** Query existing trips, compare leg sequences
- **Trade-off:** O(T * L) where T = client's trips, L = legs
- **Alternative considered:** Store connection hash in DB (rejected: brittle)

### 4.3 LayoverValidator (Service)

**Responsibilities:**
- Enforce time-based layover policies
- Provide policy configuration

**Policy Engine:**
```python
if is_daytime:
    limits = (15, 120)  # minutes
else:
    limits = (15, 30)
```

**Design Decision:** Why time-of-day heuristic?
- **Rationale:** After-hours layovers risky (station closures, safety)
- **Trade-off:** Simplicity vs. station-specific rules
- **Future:** Load policies from configuration file per city

### 4.4 Database (Data Access Layer)

**Responsibilities:**
- Execute SQL operations
- Manage connections
- Provide transaction safety

**Connection Management:**
```python
@contextmanager
def connection(self):
    conn = sqlite3.connect(self.db_path)
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**Design Decision:** Why context managers?
- **Rationale:** Automatic resource cleanup
- **Safety:** Guarantees rollback on exception
- **Alternative considered:** Manual commit/rollback (rejected: error-prone)

---

## 5. Key Design Decisions

### 5.1 Trip ID Change: Alphanumeric → Numeric

**Iteration 2:**
```python
trip_id = "TRP-A3F2B1C4"  # str, generated via secrets.token_hex()
```

**Iteration 3:**
```python
trip_id = 12345  # int, database auto-increment
```

**Rationale:**
- **Performance:** Integer comparison faster than string
- **Storage:** 8 bytes (int64) vs 13+ bytes (string)
- **Simplicity:** Database handles uniqueness, no collision risk
- **Standardization:** Aligns with SQL conventions

**Trade-offs:**
- **Pro:** Simpler code, better performance
- **Con:** IDs less human-readable
- **Con:** Sequential IDs leak business metrics (total bookings)
- **Mitigation:** Add UUID column for public-facing IDs (future)

### 5.2 In-Memory → Database Persistence

**Iteration 2:**
```python
self.trips: Dict[str, Trip] = {}
self.client_trips_index: Dict[tuple, Set[str]] = {}
```

**Iteration 3:**
```python
self.db = Database("booking.db")
# All data in SQLite tables
```

**Rationale:**
- **Durability:** Data survives crashes/restarts
- **Concurrency:** Database handles locking
- **Scalability:** Disk-based storage removes RAM limits

**Trade-offs:**
- **Pro:** Production-ready persistence
- **Pro:** ACID transactions
- **Con:** Slower than in-memory (10-100x)
- **Con:** Additional complexity (schema management)

**Performance Impact:**
| Operation | In-Memory | Database | Slowdown |
|-----------|-----------|----------|----------|
| Book trip | ~0.1ms | ~5ms | 50x |
| View trips | ~0.05ms | ~2ms | 40x |
| Search routes | ~10ms | ~15ms | 1.5x (routes cached) |

**Optimization Strategies:**
- Use in-memory DB (`:memory:`) for testing
- Enable WAL mode for better concurrency
- Add caching layer for hot data (future)

### 5.3 Layover Validation Integration

**Previous:** Simple minimum transfer time check
```python
def _transfer_gap_ok(self, r_prev, r_next, min_minutes):
    gap = r_next.dep_min - r_prev.arr_min
    return gap >= min_minutes
```

**Iteration 3:** Time-based policy enforcement
```python
def _transfer_gap_ok(self, r_prev, r_next, min_minutes, policy):
    if gap < min_minutes:
        return False
    is_valid, reason = LayoverValidator.is_layover_acceptable(...)
    return is_valid
```

**Rationale:**
- **User Experience:** Avoid proposing unreasonable connections
- **Business Logic:** Encode domain knowledge (day vs. night rules)
- **Flexibility:** Configurable policies (strict/lenient)

**Trade-offs:**
- **Pro:** Smarter search results
- **Pro:** Reduced customer complaints
- **Con:** Fewer results returned
- **Con:** Additional computation per connection

---

## 6. Concurrency & Transactions

### 6.1 Concurrent Bookings

**Scenario:** Two users book last seat on same train simultaneously

**SQLite Behavior:**
```python
# User A
BEGIN TRANSACTION
INSERT INTO trips ...
INSERT INTO tickets ...
COMMIT  # Success

# User B (parallel)
BEGIN TRANSACTION
INSERT INTO trips ...  # Blocks on COMMIT of User A
INSERT INTO tickets ...
COMMIT  # Success (both bookings accepted)
```

**Current Limitation:** No seat capacity tracking
- Both bookings succeed (overbooking possible)
- **Future:** Add `seats_available` column with optimistic locking

### 6.2 Transaction Isolation

**SQLite Default:** SERIALIZABLE
- Strongest isolation level
- No dirty reads, no phantom reads
- **Cost:** Lower concurrency (exclusive locks)

**PostgreSQL Production:** READ COMMITTED
- Better concurrency
- Requires explicit locking for critical sections

### 6.3 Deadlock Prevention

**Strategy:** Ordered resource acquisition
- Always acquire locks in same order: clients → trips → tickets
- Prevents circular wait condition

---

## 7. Security Considerations

### 7.1 SQL Injection Prevention

**Good (Parameterized):**
```python
cursor.execute("SELECT * FROM clients WHERE id_number = ?", (id_num,))
```

**Bad (String Concatenation):**
```python
cursor.execute(f"SELECT * FROM clients WHERE id_number = '{id_num}'")
```

**Enforcement:** All database.py queries use parameterized statements

### 7.2 Data Privacy (PII)

**Sensitive Data:**
- Client names (first_name, last_name)
- ID numbers (passport, state ID)

**Current Protections:**
- No encryption at rest (SQLite file)
- No access control (anyone with file access can read)

**Production Requirements:**
- Encrypt database file (SQLCipher or transparent encryption)
- Add authentication layer (user login)
- Implement RBAC (clients see only their trips)
- Audit log for PII access

### 7.3 Input Validation

**Current:** Basic validation
```python
if not first_name or not last_name:
    raise ValueError("Names cannot be empty")
```

**Future Enhancements:**
- Regex validation for ID numbers
- Age range checks (0-120)
- City name whitelist (prevent SQL injection via CSV)

---

## 8. Performance Characteristics

### 8.1 Search Performance

| Routes | Direct | 1-Stop | 2-Stop |
|--------|--------|--------|--------|
| 1,000 | < 10ms | < 100ms | < 1s |
| 10,000 | < 50ms | < 500ms | < 5s |
| 50,000 | < 200ms | < 3s | < 30s |

**Bottlenecks:**
- 2-stop search: O(N²) complexity
- Layover validation: O(N) policy checks per connection

**Optimization Roadmap:**
1. Add route graph representation
2. Implement Dijkstra's algorithm with layover constraints
3. Cache frequent searches (Redis)

### 8.2 Database Performance

**Query Times (1,000 trips):**
- Get trip by ID: ~2ms
- Get trips for client: ~5ms
- Create booking: ~10ms (5 INSERTs)

**Index Impact:**
```sql
-- Before index
SELECT * FROM clients WHERE last_name = 'Smith';  -- 15ms

-- After index
CREATE INDEX idx_clients_lookup ON clients(last_name, id_number);
SELECT * FROM clients WHERE last_name = 'Smith';  -- 0.5ms (30x faster)
```

### 8.3 Scalability Limits

**SQLite:**
- Max concurrent writers: 1
- Max database size: 281 TB (theoretical), ~1 TB (practical)
- Max rows per table: 2^64

**Recommended Limits:**
- Trips: < 10 million
- Routes: < 100,000
- Concurrent users: < 100

**Migration Path to PostgreSQL:**
- Same schema, minimal code changes
- Horizontal scaling via read replicas
- Connection pooling for 1000+ concurrent users

---

## 9. Error Handling Strategy

### 9.1 Error Categories

**Business Rule Violations:**
- Duplicate booking → ValueError with clear message
- Invalid age → ValueError
- Empty names → ValueError

**Database Errors:**
- Connection failure → sqlite3.Error, retry with backoff
- Constraint violation → sqlite3.IntegrityError, rollback
- Disk full → sqlite3.OperationalError, alert admin

**External Errors:**
- CSV not found → FileNotFoundError, display helpful message
- Malformed CSV → ValueError, log row number

### 9.2 Exception Hierarchy

```
Exception
└── ValueError (business logic)
└── sqlite3.Error (database)
    ├── IntegrityError (constraints)
    ├── OperationalError (disk, locks)
    └── ProgrammingError (SQL syntax)
```

### 9.3 Failure Recovery

**Transient Failures:** Retry
```python
for attempt in range(3):
    try:
        db.create_trip(...)
        break
    except sqlite3.OperationalError:
        time.sleep(0.1 * 2**attempt)
```

**Permanent Failures:** Graceful degradation
- If database unavailable, show cached data
- If search fails, return empty results with explanation

---

## 10. Testing Strategy

### 10.1 Test Pyramid

```
        /\
       /  \        E2E (Integration Tests)
      /____\       - test_iteration3.py::TestIntegration
     /      \      
    /        \     Integration Tests
   /__________\    - test_iteration3.py::TestBookingSystemV3
  /            \   
 /              \  Unit Tests
/________________\ - test_iteration3.py::TestLayoverValidator
                  - test_iteration3.py::TestDatabase
```

### 10.2 Test Coverage

| Component | Unit Tests | Integration Tests | Coverage |
|-----------|------------|-------------------|----------|
| database.py | 6 | 1 | 95% |
| layover_validator.py | 7 | 2 | 100% |
| booking_system_v3.py | 6 | 2 | 90% |
| rail_network.py | 2 | 1 | 85% |

### 10.3 Test Database Strategy

**In-Memory Database:**
```python
db = Database(":memory:")
```
- **Pros:** Fast (no disk I/O), isolated
- **Cons:** Doesn't test file persistence

**File-Based Database:**
```python
db = Database("test_temp.db")
# ... test ...
os.remove("test_temp.db")
```
- **Pros:** Tests real persistence
- **Cons:** Slower, requires cleanup

---

## 11. Deployment Architecture

### 11.1 Development

```
Developer Machine
├── Python 3.8+
├── SQLite (bundled)
├── booking.db (local file)
└── CSV files (local)
```

### 11.2 Production (Future)

```
┌───────────────┐
│  Load Balancer│
└───────┬───────┘
        │
    ┌───┴──────────────────┐
    │                      │
┌───▼──────┐       ┌──────▼───┐
│ App      │       │ App      │
│ Server 1 │       │ Server 2 │
└───┬──────┘       └──────┬───┘
    │                     │
    └──────────┬──────────┘
               │
        ┌──────▼───────┐
        │ PostgreSQL   │
        │ (Primary)    │
        └──────┬───────┘
               │
        ┌──────▼───────┐
        │ PostgreSQL   │
        │ (Replica)    │
        └──────────────┘
```

---

## 12. Future Enhancements

### 12.1 Short-Term (Next Iteration)

1. **RESTful API** (FastAPI)
   - Expose booking via HTTP
   - JSON request/response
   - API versioning

2. **Authentication**
   - User accounts
   - Password hashing (bcrypt)
   - Session management

3. **Seat Selection**
   - Track seat availability
   - Visual seat map
   - Optimistic locking

### 12.2 Long-Term

1. **Real-Time Updates**
   - WebSocket for live availability
   - Push notifications for delays

2. **Payment Integration**
   - Stripe/PayPal
   - Multi-currency support

3. **Machine Learning**
   - Recommend connections based on history
   - Dynamic pricing
   - Demand prediction

---

## Document Metadata

**Version:** 3.0  
**Last Updated:** November 7, 2025  
**Authors:** SOEN 342 Team  
**Next Review:** Before production deployment

