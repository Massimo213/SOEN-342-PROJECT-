# QUICK DEMO CHEAT SHEET - 5 MINUTES

## PREP (Before recording)
```bash
cd /Users/yahyamounadi/Desktop/Soen-342
clear
# Increase terminal font size: Cmd + Plus
```

---

## [0:00-0:30] INTRO
**Say:** "Rail Network Booking System - complete software system across four iterations."

```bash
ls -la
echo "Documentation: 7 files | UML: 6 diagrams | Code: 4,011 lines | Tests: 44"
```

---

## [0:30-1:15] ITERATION 1: Search
**Say:** "Search system with direct and multi-stop connections."

```bash
python3 app.py --csv eu_rail_network.csv --from Amsterdam --to Brussels --max-stops 0 --format table --limit 2

python3 app.py --csv eu_rail_network.csv --from Amsterdam --to Vienna --max-stops 1 --format table --limit 2
```

---

## [1:15-2:00] ITERATION 2: Booking
**Say:** "Trip booking with unique ticket IDs and history tracking."

```bash
python3 -c "
from rail_network import RailNetwork
from booking_system import BookingSystem

network = RailNetwork.from_csv('eu_rail_network.csv')
booking = BookingSystem()
connections = network.search(departure_city='Amsterdam', arrival_city='Brussels', max_stops=0)
trip = booking.book_trip(connections[0], [('John', 'Smith', 'PASS001', 45)])
print(f'Trip ID: {trip.trip_id}')
print(f'Ticket IDs: {[r.ticket.ticket_id for r in trip.reservations]}')
"
```

---

## [2:00-3:00] ITERATION 3: Database & Layover
**Say:** "Database persistence and smart layover validation."

```bash
python3 -c "
from database import Database
db = Database(':memory:')
count = db.load_routes_from_csv('eu_rail_network.csv')
print(f'Loaded {count} routes')
print(f'Statistics: {db.get_statistics()}')
"

python3 -c "
from layover_validator import LayoverValidator
v1, r1 = LayoverValidator.is_layover_acceptable(10*60, 11*60, 'strict')
v2, r2 = LayoverValidator.is_layover_acceptable(23*60, 23*60+45, 'strict')
print(f'60min daytime: {v1} - {r1}')
print(f'45min after-hours: {v2} - {r2}')
"

python3 -c "
from database import Database
from booking_system_v3 import BookingSystem
from rail_network import RailNetwork

db = Database(':memory:')
db.load_routes_from_csv('eu_rail_network.csv')
booking = BookingSystem(db)
network = RailNetwork.from_csv('eu_rail_network.csv')
connections = network.search(departure_city='Amsterdam', arrival_city='Brussels', max_stops=0)
trip = booking.book_trip(connections[0], [('Alice', 'Demo', 'DEMO001', 30)])
print(f'Numeric Trip ID: {trip.trip_id}')
"
```

---

## [3:00-4:00] FINAL: OCL & State Machine
**Say:** "Formal specifications and state machine implementation."

```bash
head -40 docs/ocl-constraints.md | tail -20

python3 -c "
from database import Database
from booking_system_v3 import BookingSystem
from rail_network import RailNetwork

db = Database(':memory:')
db.load_routes_from_csv('eu_rail_network.csv')
booking = BookingSystem(db)
network = RailNetwork.from_csv('eu_rail_network.csv')
connections = network.search(departure_city='Amsterdam', arrival_city='Brussels', max_stops=0)
trip = booking.book_trip(connections[0], [('Bob', 'Test', 'TEST001', 40)])
print(f'✓ First booking: Trip {trip.trip_id}')

try:
    booking.book_trip(connections[0], [('Bob', 'Test', 'TEST001', 40)])
except ValueError:
    print('✓ OCL constraint enforced: Duplicate prevented')
"

head -80 diagrams/state-machine-booking.puml | tail -40

python3 -c "
from database import Database
from booking_system_v3 import BookingSystem
from rail_network import RailNetwork
from booking_state_machine import BookingStateMachine

db = Database(':memory:')
db.load_routes_from_csv('eu_rail_network.csv')
booking = BookingSystem(db)
network = RailNetwork.from_csv('eu_rail_network.csv')

sm = BookingStateMachine(network, booking)
print(f'State: {sm.get_current_state().name}')
sm.start_booking('Amsterdam', 'Brussels')
print(f'State: {sm.get_current_state().name}')
sm.select_connection(0)
sm.add_travelers([('State', 'Machine', 'SM001', 25)])
sm.execute_current_state()
sm.execute_current_state()
print(f'State: {sm.get_current_state().name}')
print(f'Trip ID: {sm.context.trip_id}')
" 2>&1 | grep -v "TRANSITION" | grep -v "===" | head -10
```

---

## [4:00-5:00] Documentation & Tests
**Say:** "Professional documentation and comprehensive testing."

```bash
echo "=== DOCUMENTATION ==="
ls -lh docs/
echo ""
echo "=== UML DIAGRAMS ==="
ls -lh diagrams/*.puml

python3 test_iteration3.py 2>&1 | tail -10
python3 test_final_iteration.py 2>&1 | tail -10

git log --oneline -3
git tag -l

cat << 'EOF'
╔═══════════════════════════════════════════════════════╗
║         COMPLETE SOFTWARE SYSTEM                      ║
╠═══════════════════════════════════════════════════════╣
║  Requirements:    10 FR, 7 NFR                        ║
║  Use Cases:       4 detailed specs                    ║
║  UML Diagrams:    6 diagrams                          ║
║  OCL Specs:       Formal specifications               ║
║  Implementation:  4,011 lines                         ║
║  Tests:           44 tests, 100% passing              ║
║  Documentation:   3,453 lines                         ║
╚═══════════════════════════════════════════════════════╝

Complete software development lifecycle demonstrated:
Requirements → Design → Implementation → Testing → Deployment
EOF
```

---

## CLOSING
**Say:** "This demonstrates a complete software system following industry standards. Requirements, UML design, formal OCL, database architecture, comprehensive testing, and deployment documentation. The complete engineering process. Thank you."

---

## KEY PHRASES TO USE
- "Complete software system, not just code"
- "Six UML diagrams from multiple perspectives"
- "Formal OCL specifications enforced at runtime"
- "Forty-four tests, all passing"
- "Complete engineering lifecycle"

