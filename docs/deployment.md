# Deployment Guide
**SOEN 342 - Rail Network Booking System - Iteration 3**  
**Version:** 3.0  
**Date:** November 7, 2025

---

## 1. System Requirements

### 1.1 Prerequisites

**Required:**
- Python 3.8 or higher
- SQLite 3.35+ (bundled with Python)
- 100 MB disk space (database + CSV data)
- 512 MB RAM minimum

**Recommended:**
- Python 3.11+
- 1 GB RAM
- SSD for database storage

### 1.2 Supported Platforms

| Platform | Tested | Status |
|----------|--------|--------|
| macOS 11+ | ✅ | Fully supported |
| Linux (Ubuntu 20.04+) | ✅ | Fully supported |
| Windows 10/11 | ✅ | Fully supported |
| Docker | ✅ | Container available |

---

## 2. Installation

### 2.1 Quick Start (Local Development)

```bash
# Clone repository
git clone https://github.com/your-org/Soen-342.git
cd Soen-342

# Verify Python version
python3 --version  # Should be 3.8+

# No external dependencies required!
# The system uses only Python standard library

# Verify installation
python3 -c "import sqlite3; print('SQLite version:', sqlite3.sqlite_version)"
```

**Expected Output:**
```
SQLite version: 3.37.0
```

### 2.2 Project Structure

After installation, your directory should look like:

```
Soen-342/
├── database.py                  # Database layer
├── booking_system_v3.py         # Business logic (Iteration 3)
├── rail_network.py              # Search engine
├── layover_validator.py         # Policy enforcement
├── booking_cli.py               # Interactive CLI (legacy)
├── app.py                       # Search CLI
├── eu_rail_network.csv          # Route data
├── test_iteration3.py           # Test suite
├── docs/                        # Documentation
│   ├── requirements.md
│   ├── use-cases.md
│   ├── data-model.md
│   ├── architecture.md
│   └── deployment.md
├── diagrams/                    # UML diagrams
│   ├── class-diagram.puml
│   ├── usecase-diagram.puml
│   └── sequence-*.puml
└── README.md
```

---

## 3. Configuration

### 3.1 Database Configuration

**Development (default):**
```python
# In your code:
from database import Database

db = Database("booking.db")  # Creates file in current directory
```

**Testing (in-memory):**
```python
db = Database(":memory:")  # No file created, fastest
```

**Production:**
```python
# Use absolute path for production database
db = Database("/var/data/rail-booking/booking.db")
```

### 3.2 Environment Variables (Optional)

```bash
# Set database path
export RAIL_DB_PATH="/path/to/booking.db"

# Set layover policy
export LAYOVER_POLICY="strict"  # or "lenient"

# Set CSV data path
export ROUTE_CSV="/path/to/routes.csv"
```

**Using in code:**
```python
import os
db_path = os.getenv("RAIL_DB_PATH", "booking.db")
db = Database(db_path)
```

---

## 4. First-Time Setup

### 4.1 Initialize Database

```python
#!/usr/bin/env python3
"""setup_database.py - Initialize database with routes"""

from database import Database

# Create database (creates schema automatically)
db = Database("booking.db")

# Load routes from CSV
count = db.load_routes_from_csv("eu_rail_network.csv")

print(f"Database initialized with {count} routes")
print("Ready to accept bookings!")
```

Run:
```bash
python3 setup_database.py
```

**Expected Output:**
```
Database initialized with 1247 routes
Ready to accept bookings
```

### 4.2 Verify Installation

```bash
# Run test suite
python3 test_iteration3.py
```

**Expected Output (excerpt):**
```
test_schema_creation (test_iteration3.TestDatabase) ... ok
test_load_routes_from_csv (test_iteration3.TestDatabase) ... ok
test_book_single_traveler (test_iteration3.TestBookingSystemV3) ... ok
...
----------------------------------------------------------------------
Ran 28 tests in 3.456s

OK
All tests passed
```

---

## 5. Usage Examples

### 5.1 Programmatic API Usage

#### Example 1: Search and Book

```python
#!/usr/bin/env python3
"""example_booking.py"""

from database import Database
from booking_system_v3 import BookingSystem
from rail_network import RailNetwork

# Initialize
db = Database("booking.db")
db.load_routes_from_csv("eu_rail_network.csv")

network = RailNetwork.from_csv("eu_rail_network.csv")
booking_system = BookingSystem(db)

# Search for connections
connections = network.search(
    departure_city="Paris",
    arrival_city="Berlin",
    max_stops=1,
    layover_policy="strict",
    sort_by="duration"
)

print(f"Found {len(connections)} connections")

# Book first connection
if connections:
    trip = booking_system.book_trip(
        connections[0],
        [
            ("John", "Smith", "PASS001", 45),
            ("Jane", "Smith", "PASS002", 42)
        ]
    )
    
    print(f"Booking successful!")
    print(f"Trip ID: {trip.trip_id}")
    print(f"Travelers: {trip.total_travelers()}")
    print(f"Departure: {trip.departure_date()}")
```

Run:
```bash
python3 example_booking.py
```

#### Example 2: View Trip History

```python
#!/usr/bin/env python3
"""example_view_trips.py"""

from database import Database
from booking_system_v3 import BookingSystem

db = Database("booking.db")
booking_system = BookingSystem(db)

# Retrieve trips for client
current, past = booking_system.get_trips_by_client("Smith", "PASS001")

print(f"Current trips: {len(current)}")
for trip in current:
    print(f"  Trip {trip.trip_id}: {trip.connection.origin} → {trip.connection.destination}")

print(f"\nPast trips: {len(past)}")
for trip in past:
    print(f"  Trip {trip.trip_id}: {trip.connection.origin} → {trip.connection.destination}")
```

### 5.2 Command-Line Usage

#### Search for Connections

```bash
python3 app.py \
  --csv eu_rail_network.csv \
  --from "Amsterdam" \
  --to "Brussels" \
  --max-stops 1 \
  --min-transfer 20 \
  --class second \
  --sort duration \
  --format table
```

**Output:**
```
origin     | destination | depart | arrive | stops | trip_duration(min) | transfer_time(min) | total_price_second | legs
-----------|-------------|--------|--------|-------|--------------------|--------------------|--------------------|-----------------
Amsterdam  | Brussels    | 10:15  | 12:30  | 0     | 135                | 0                  | 45.00              | Amsterdam(10:15)→Brussels(12:30)
Amsterdam  | Brussels    | 09:30  | 13:00  | 1     | 210                | 30                 | 68.00              | Amsterdam(09:30)→Rotterdam(11:00) → Rotterdam(11:30)→Brussels(13:00)
```

---

## 6. Running Tests

### 6.1 Full Test Suite

```bash
python3 test_iteration3.py
```

### 6.2 Specific Test Categories

```bash
# Test only database
python3 -m unittest test_iteration3.TestDatabase

# Test only layover validator
python3 -m unittest test_iteration3.TestLayoverValidator

# Test only booking system
python3 -m unittest test_iteration3.TestBookingSystemV3
```

### 6.3 Verbose Output

```bash
python3 test_iteration3.py -v
```

---

## 7. Database Management

### 7.1 Viewing Database Contents

**Using SQLite CLI:**
```bash
sqlite3 booking.db
```

```sql
-- View schema
.schema

-- View routes
SELECT COUNT(*) FROM routes;

-- View recent bookings
SELECT trip_id, departure_city, arrival_city, booking_timestamp 
FROM trips 
ORDER BY booking_timestamp DESC 
LIMIT 10;

-- View clients
SELECT client_id, first_name, last_name, id_number 
FROM clients;
```

**Using Python:**
```python
from database import Database

db = Database("booking.db")
stats = db.get_statistics()

for table, count in stats.items():
    print(f"{table}: {count} records")
```

### 7.2 Backup Database

```bash
# Simple file copy
cp booking.db booking_backup_$(date +%Y%m%d).db

# Using SQLite backup command
sqlite3 booking.db ".backup booking_backup.db"
```

### 7.3 Reset Database

```bash
# WARNING: Deletes all data!
rm booking.db
python3 setup_database.py
```

**Or in Python:**
```python
db = Database("booking.db")
db.clear_all_data()  # Keeps schema, deletes data
db.load_routes_from_csv("eu_rail_network.csv")
```

---

## 8. Performance Tuning

### 8.1 SQLite Optimizations

**Enable WAL mode for better concurrency:**
```python
with db.connection() as conn:
    conn.execute("PRAGMA journal_mode = WAL")
```

**Increase cache size:**
```python
with db.connection() as conn:
    conn.execute("PRAGMA cache_size = -64000")  # 64 MB cache
```

**Disable synchronous writes (dev only):**
```python
# WARNING: Risk of data loss on crash!
with db.connection() as conn:
    conn.execute("PRAGMA synchronous = OFF")
```

### 8.2 Application-Level Caching

```python
from functools import lru_cache

class RailNetwork:
    @lru_cache(maxsize=100)
    def search(self, departure_city, arrival_city, ...):
        # Cached search results
        ...
```

---

## 9. Troubleshooting

### 9.1 Common Issues

#### Issue: "database is locked"

**Cause:** Multiple writers accessing SQLite simultaneously

**Solution:**
```python
# Increase busy timeout
db = Database("booking.db")
with db.connection() as conn:
    conn.execute("PRAGMA busy_timeout = 10000")  # 10 seconds
```

#### Issue: "no such table: routes"

**Cause:** Database not initialized

**Solution:**
```bash
python3 setup_database.py
```

#### Issue: "duplicate column name"

**Cause:** Schema migration conflict

**Solution:**
```bash
# Delete and recreate database
rm booking.db
python3 setup_database.py
```

#### Issue: "CSV file not found"

**Cause:** Incorrect path to eu_rail_network.csv

**Solution:**
```python
import os
print(os.getcwd())  # Check current directory
db.load_routes_from_csv("./eu_rail_network.csv")  # Use relative path
```

### 9.2 Debug Mode

**Enable SQL logging:**
```python
import sqlite3
sqlite3.enable_callback_tracebacks(True)

# Log all SQL queries
conn.set_trace_callback(print)
```

**Enable verbose output:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 10. Production Deployment

### 10.1 Migration to PostgreSQL

**Install psycopg2:**
```bash
pip install psycopg2-binary
```

**Update database.py:**
```python
import psycopg2

class Database:
    def __init__(self, connection_string):
        self.conn_string = connection_string
    
    def connection(self):
        return psycopg2.connect(self.conn_string)
```

**Connection string:**
```python
db = Database("postgresql://user:pass@localhost:5432/rail_booking")
```

### 10.2 Containerization (Docker)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN python3 setup_database.py

EXPOSE 8000

CMD ["python3", "-m", "http.server", "8000"]
```

**Build and run:**
```bash
docker build -t rail-booking .
docker run -p 8000:8000 -v $(pwd)/booking.db:/app/booking.db rail-booking
```

### 10.3 Systemd Service (Linux)

**/etc/systemd/system/rail-booking.service:**
```ini
[Unit]
Description=Rail Network Booking System
After=network.target

[Service]
Type=simple
User=rail
WorkingDirectory=/opt/rail-booking
ExecStart=/usr/bin/python3 /opt/rail-booking/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable rail-booking
sudo systemctl start rail-booking
```

---

## 11. Monitoring

### 11.1 Database Statistics

```python
def monitor_db():
    db = Database("booking.db")
    stats = db.get_statistics()
    
    print(f"Routes: {stats['routes']}")
    print(f"Active bookings: {stats['trips']}")
    print(f"Total tickets issued: {stats['tickets']}")
    
    # Check database size
    import os
    size_mb = os.path.getsize("booking.db") / (1024 * 1024)
    print(f"Database size: {size_mb:.2f} MB")
```

### 11.2 Performance Metrics

```python
import time

def benchmark_search():
    start = time.time()
    
    network = RailNetwork.from_csv("eu_rail_network.csv")
    connections = network.search(
        departure_city="Paris",
        arrival_city="Berlin",
        max_stops=2
    )
    
    elapsed = time.time() - start
    print(f"Search took {elapsed:.3f}s, found {len(connections)} connections")
```

---

## 12. Security Checklist

### 12.1 Pre-Production

- [ ] Enable database encryption (SQLCipher)
- [ ] Implement user authentication
- [ ] Add input validation for all user inputs
- [ ] Enable HTTPS for web interface
- [ ] Set up database backups (automated)
- [ ] Configure firewall rules
- [ ] Review SQL injection prevention
- [ ] Implement rate limiting
- [ ] Add audit logging
- [ ] Set up monitoring alerts

### 12.2 Production

- [ ] Use environment variables for secrets
- [ ] Rotate database credentials regularly
- [ ] Enable SSL for database connections
- [ ] Set up intrusion detection
- [ ] Perform security audit
- [ ] Document incident response plan
- [ ] Configure log retention policy
- [ ] Implement GDPR compliance measures

---

## 13. Support and Resources

### 13.1 Documentation

- **Requirements:** `docs/requirements.md`
- **Use Cases:** `docs/use-cases.md`
- **Architecture:** `docs/architecture.md`
- **Data Model:** `docs/data-model.md`
- **UML Diagrams:** `diagrams/README.md`

### 13.2 Useful Commands

```bash
# Quick health check
python3 -c "from database import Database; db = Database('booking.db'); print(db.get_statistics())"

# View last 10 bookings
sqlite3 booking.db "SELECT * FROM trips ORDER BY booking_timestamp DESC LIMIT 10"

# Count active clients
sqlite3 booking.db "SELECT COUNT(DISTINCT client_id) FROM tickets"

# Database integrity check
sqlite3 booking.db "PRAGMA integrity_check"
```

### 13.3 Getting Help

**Common Issues:**
1. Check `docs/architecture.md` Section 9 (Error Handling)
2. Run `python3 test_iteration3.py` to verify setup
3. Check SQLite version: `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`

**Contact:**
- Project Repository: [GitHub/your-org/Soen-342]
- Course Instructor: [instructor-email]
- TA: [ta-email]

---

## Document Metadata

**Version:** 3.0  
**Last Updated:** November 7, 2025  
**Maintainer:** SOEN 342 Team  
**Next Review:** Before production deployment

