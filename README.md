# Rail Network Booking System — Iteration 2

Production-grade rail booking system implementing SOEN 342 requirements.

## Architecture Overview

```
┌─────────────────┐
│  booking_cli.py │  ← User interface (search, book, view trips)
└────────┬────────┘
         │
    ┌────▼───────────────┐
    │ booking_system.py  │  ← Core domain logic
    │  - Client          │
    │  - Ticket          │
    │  - Reservation     │
    │  - Trip            │
    │  - BookingSystem   │
    └────────┬───────────┘
             │
        ┌────▼────────────┐
        │ rail_network.py │  ← Route catalog & search
        │  - TrainRoute   │
        │  - Itinerary    │
        │  - RailNetwork  │
        └─────────────────┘
```

## Features

### ✅ Iteration 1 (Completed)
- Load routes from CSV
- Search direct, 1-stop, 2-stop connections
- Filter by city, train type, days of operation
- Sort by duration or price
- CLI and programmatic API

### ✅ Iteration 2 (Completed)
- **Trip booking** for single or multiple travelers
- **Unique IDs**: Alphanumeric trip IDs, numeric ticket IDs
- **Business rules**:
  - One reservation per client per connection
  - No duplicate travelers in single trip
  - Immutable tickets (audit trail)
- **Trip viewing** by client credentials (last name + ID)
- **History management**: Separate current and past trips
- **Client registry**: Automatic deduplication

## Quick Start

### Installation
```bash
# No external dependencies required (pure Python 3.8+)
git clone <repo>
cd Soen-342
```

### Run Tests
```bash
python3 test_booking.py
```

### Search for Connections
```bash
python3 app.py --csv eu_rail_network.csv \
    --from "Paris" --to "Berlin" \
    --sort duration --class second \
    --max-stops 2 --min-transfer 20
```

### Book a Trip (Interactive)
```bash
python3 booking_cli.py book \
    --csv eu_rail_network.csv \
    --from "Amsterdam" --to "Brussels"

# Follow prompts to:
# 1. Select connection
# 2. Enter traveler details
# 3. Confirm booking
```

### View Your Trips
```bash
python3 booking_cli.py view-trips \
    --csv eu_rail_network.csv \
    --last-name Smith \
    --id PASS001
```

## Usage Examples

### Scenario 1: Family Booking
```python
from rail_network import RailNetwork
from booking_system import BookingSystem

# Load network
network = RailNetwork.from_csv("eu_rail_network.csv")

# Search connection
connections = network.search(
    departure_city="Paris",
    arrival_city="Rome",
    max_stops=1
)

# Book for family of 4
booking = BookingSystem()
trip = booking.book_trip(connections[0], [
    ("John", "Smith", "PASS001", 45),
    ("Jane", "Smith", "PASS002", 42),
    ("Emily", "Smith", "PASS003", 16),
    ("Michael", "Smith", "PASS004", 12)
])

print(f"Trip ID: {trip.trip_id}")
print(f"Travelers: {trip.total_travelers()}")
```

### Scenario 2: Solo Traveler
```python
trip = booking.book_trip(connections[0], [
    ("Alice", "Johnson", "ID789", 28)
])

ticket = trip.reservations[0].ticket
print(f"Ticket #{ticket.ticket_id}")
```

## Design Decisions

### 1. Immutability
- `Client` and `Ticket` are frozen dataclasses
- Prevents accidental modification
- Enables use as dict keys/set members
- Audit trail compliance

### 2. ID Generation
**Trip IDs** (`TRP-{8-hex}`):
- Collision resistance: ~1 in 4 billion
- Human-readable prefix
- Case-insensitive for user input

**Ticket IDs** (15-digit numeric):
- Timestamp-based: 10 digits
- Random component: 5 digits
- Sortable by issue time
- Numeric for legacy system compatibility

### 3. Client Identity
Hash based on `(last_name, id_number)`:
- Natural key (passport/state-id)
- Case-insensitive last name
- Automatic deduplication in sets
- Fast O(1) lookup

### 4. Indexing Strategy
```python
client_trips_index: Dict[tuple, Set[str]]
# (last_name.lower(), id_number) -> {trip_ids}
```
- O(1) trip lookup by credentials
- Memory overhead: ~40 bytes per client-trip pair
- Scales linearly with bookings

### 5. Connection Equality
Compares route IDs in order:
```python
[R001, R002, R003] == [R001, R002, R003]  # True
[R001, R002] ≠ [R002, R001]              # False (different order)
```

## Performance Characteristics

| Operation | Time Complexity | Space |
|-----------|----------------|-------|
| Book trip | O(N + M log M) | O(N) |
| View trips | O(1) average | O(1) |
| Search connections | O(R²) worst | O(R) |

Where:
- N = travelers in booking
- M = matching connections
- R = total routes

### Bottlenecks
1. **2-stop search**: O(R²) triple-nested loop
   - Mitigation: Index by departure city
   - Future: Graph-based pathfinding

2. **Connection comparison**: O(L) per comparison
   - L = legs in itinerary
   - Pre-compute connection signatures for O(1)

## Testing

### Coverage
- ✅ ID generation uniqueness
- ✅ Client identity/deduplication
- ✅ Family booking (Scenario 1)
- ✅ Solo traveler (Scenario 2)
- ✅ Duplicate booking prevention
- ✅ Duplicate traveler prevention
- ✅ Multi-trip viewing
- ✅ Validation errors

### Run All Tests
```bash
python3 test_booking.py
```

## Failure Modes

1. **ID Collision**: Probability ~10⁻⁹ per booking
   - Mitigation: Check existence before use
   - Recovery: Regenerate ID

2. **Concurrent Bookings**: NOT thread-safe
   - Mitigation: Add `threading.Lock` on booking_system
   - Production: Use database transactions

3. **Memory Exhaustion**: Linear growth with bookings
   - Mitigation: Implement trip archival
   - Production: Paginate trip history

4. **Date Parsing**: Current data lacks full dates
   - Workaround: Heuristic based on booking timestamp
   - Production: Require ISO8601 dates

## Limitations & Future Work

### Known Limitations
- In-memory storage (not persistent)
- No payment processing
- No seat allocation
- No trip cancellation
- Past/current trip logic simplified (needs full dates)

### Iteration 3 Ideas
- [ ] Persistent storage (SQLite/PostgreSQL)
- [ ] RESTful API (FastAPI)
- [ ] Seat selection & availability
- [ ] Trip modification/cancellation
- [ ] Payment integration
- [ ] Email confirmations
- [ ] Multi-currency pricing

## Production Checklist

Before deploying to production:
- [ ] Add database layer (replace in-memory dicts)
- [ ] Implement connection pooling
- [ ] Add logging (structured JSON)
- [ ] Add metrics (Prometheus/StatsD)
- [ ] Add distributed tracing
- [ ] Implement rate limiting
- [ ] Add authentication/authorization
- [ ] Set up monitoring & alerts
- [ ] Load testing (1000+ req/s)
- [ ] Disaster recovery plan
- [ ] PII encryption at rest
- [ ] GDPR compliance (data deletion)

## Files

- `rail_network.py` — Route catalog & search engine
- `booking_system.py` — Domain models & booking logic
- `booking_cli.py` — Interactive CLI
- `app.py` — Original search CLI (Iteration 1)
- `test_booking.py` — Comprehensive test suite
- `eu_rail_network.csv` — Route data (1200 routes)

## License

Academic project for SOEN 342
