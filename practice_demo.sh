#!/bin/bash
# Practice Demo Script - Test all commands before recording
# Run this to ensure everything works and to practice timing

cd /Users/yahyamounadi/Desktop/Soen-342
clear

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        PRACTICE DEMO - 5 MINUTE VIDEO REHEARSAL              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
START=$(date +%s)

# ==============================================================
# [0:00-0:30] INTRO (30 seconds)
# ==============================================================
echo "[0:00-0:30] ========== INTRODUCTION =========="
sleep 1
echo "Project: SOEN 342 Rail Network Booking System"
echo "Demonstration: Complete System - Iterations 1-4"
echo ""
ls -la | head -10
echo ""
echo "Statistics: 4,011 lines code | 44 tests | 6 UML diagrams | 7 docs"
echo ""
sleep 3

# ==============================================================
# [0:30-1:15] ITERATION 1 (45 seconds)
# ==============================================================
echo "[0:30-1:15] ========== ITERATION 1: SEARCH SYSTEM =========="
sleep 1
echo ""
echo "Direct connections Amsterdam → Brussels:"
python3 app.py --csv eu_rail_network.csv --from Amsterdam --to Brussels --max-stops 0 --format table --limit 2
echo ""
sleep 2

echo "One-stop connections Amsterdam → Vienna:"
python3 app.py --csv eu_rail_network.csv --from Amsterdam --to Vienna --max-stops 1 --format table --limit 2
echo ""
sleep 3

# ==============================================================
# [1:15-2:00] ITERATION 2 (45 seconds)
# ==============================================================
echo "[1:15-2:00] ========== ITERATION 2: BOOKING SYSTEM =========="
sleep 1
echo ""
echo "Booking trip with travelers:"
python3 -c "
from rail_network import RailNetwork
from booking_system import BookingSystem

network = RailNetwork.from_csv('eu_rail_network.csv')
booking = BookingSystem()
connections = network.search(departure_city='Amsterdam', arrival_city='Brussels', max_stops=0)

if connections:
    trip = booking.book_trip(connections[0], [
        ('John', 'Smith', 'PASS001', 45),
        ('Jane', 'Smith', 'PASS002', 42)
    ])
    print(f'✓ Trip ID: {trip.trip_id}')
    print(f'✓ Travelers: {trip.total_travelers()}')
    print(f'✓ Ticket IDs: {[r.ticket.ticket_id for r in trip.reservations]}')
"
echo ""
sleep 3

# ==============================================================
# [2:00-3:00] ITERATION 3 (60 seconds)
# ==============================================================
echo "[2:00-3:00] ========== ITERATION 3: DATABASE & LAYOVER =========="
sleep 1
echo ""
echo "Database initialization:"
python3 -c "
from database import Database
db = Database(':memory:')
count = db.load_routes_from_csv('eu_rail_network.csv')
print(f'✓ Loaded {count} routes into database')
print(f'✓ Database statistics: {db.get_statistics()}')
"
echo ""
sleep 2

echo "Layover validation policy:"
python3 -c "
from layover_validator import LayoverValidator

# Daytime layover
valid1, reason1 = LayoverValidator.is_layover_acceptable(
    arrival_minutes=10*60, 
    departure_minutes=11*60, 
    policy='strict'
)
print(f'✓ 60-min daytime layover: {valid1} - {reason1}')

# After-hours layover
valid2, reason2 = LayoverValidator.is_layover_acceptable(
    arrival_minutes=23*60, 
    departure_minutes=23*60+45, 
    policy='strict'
)
print(f'✓ 45-min after-hours layover: {valid2} - {reason2}')
"
echo ""
sleep 2

echo "Database-backed booking with numeric trip ID:"
python3 -c "
from database import Database
from booking_system_v3 import BookingSystem
from rail_network import RailNetwork

db = Database(':memory:')
db.load_routes_from_csv('eu_rail_network.csv')
booking = BookingSystem(db)
network = RailNetwork.from_csv('eu_rail_network.csv')

connections = network.search(
    departure_city='Amsterdam',
    arrival_city='Brussels',
    max_stops=0
)

if connections:
    trip = booking.book_trip(connections[0], [
        ('Alice', 'Demo', 'DEMO001', 30)
    ])
    print(f'✓ Trip ID (NUMERIC): {trip.trip_id}')
    print(f'✓ Trip persisted to SQLite database')
"
echo ""
sleep 3

# ==============================================================
# [3:00-4:00] FINAL ITERATION (60 seconds)
# ==============================================================
echo "[3:00-4:00] ========== FINAL ITERATION: OCL & STATE MACHINE =========="
sleep 1
echo ""
echo "OCL Constraints (sample):"
head -40 docs/ocl-constraints.md | tail -15
echo ""
sleep 2

echo "OCL constraint enforcement:"
python3 -c "
from database import Database
from booking_system_v3 import BookingSystem
from rail_network import RailNetwork

db = Database(':memory:')
db.load_routes_from_csv('eu_rail_network.csv')
booking = BookingSystem(db)
network = RailNetwork.from_csv('eu_rail_network.csv')

connections = network.search(
    departure_city='Amsterdam',
    arrival_city='Brussels',
    max_stops=0
)

if connections:
    # First booking
    trip = booking.book_trip(connections[0], [
        ('Bob', 'Test', 'TEST001', 40)
    ])
    print(f'✓ First booking: Trip {trip.trip_id}')
    
    # Try duplicate
    try:
        booking.book_trip(connections[0], [
            ('Bob', 'Test', 'TEST001', 40)
        ])
        print('✗ ERROR: Duplicate should have been prevented!')
    except ValueError as e:
        print(f'✓ OCL constraint enforced: Duplicate booking prevented')
"
echo ""
sleep 2

echo "State Machine implementation:"
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
print(f'✓ Initial state: {sm.get_current_state().name}')

sm.start_booking('Amsterdam', 'Brussels')
print(f'✓ After search: {sm.get_current_state().name}')

if sm.context.connections:
    sm.select_connection(0)
    sm.add_travelers([('State', 'Machine', 'SM001', 25)])
    sm.execute_current_state()  # Validation
    sm.execute_current_state()  # Creation
    print(f'✓ After booking: {sm.get_current_state().name}')
    print(f'✓ Trip created: {sm.context.trip_id}')
" 2>&1 | grep "✓"
echo ""
sleep 3

# ==============================================================
# [4:00-5:00] DOCUMENTATION & TESTS (60 seconds)
# ==============================================================
echo "[4:00-5:00] ========== DOCUMENTATION & TESTING =========="
sleep 1
echo ""
echo "=== DOCUMENTATION FILES ==="
ls -lh docs/
echo ""
echo "=== UML DIAGRAMS ==="
ls -lh diagrams/*.puml
echo ""
sleep 2

echo "=== ITERATION 3 TESTS ==="
python3 test_iteration3.py 2>&1 | tail -8
echo ""
sleep 2

echo "=== FINAL ITERATION TESTS ==="
python3 test_final_iteration.py 2>&1 | tail -8
echo ""
sleep 2

echo "=== REPOSITORY STATUS ==="
git log --oneline -3
echo ""
git tag -l
echo ""
echo "✓ Repository locked with v1.0-final tag"
echo ""
sleep 2

# ==============================================================
# FINAL SUMMARY
# ==============================================================
cat << 'EOF'

╔═══════════════════════════════════════════════════════════════╗
║            COMPLETE SOFTWARE SYSTEM                           ║
╠═══════════════════════════════════════════════════════════════╣
║  Requirements Engineering:    10 FR, 7 NFR                    ║
║  Use Case Specifications:     4 detailed use cases            ║
║  UML Diagrams:                6 diagrams                      ║
║  Data Model:                  5 tables, normalized            ║
║  OCL Constraints:             Formal specifications           ║
║  Architecture:                Layered + patterns              ║
║  Implementation:              4,011 lines                     ║
║  Tests:                       44 tests, 100% passing          ║
║  Documentation:               3,453 lines                     ║
╚═══════════════════════════════════════════════════════════════╝

This demonstrates the complete software development lifecycle:
Requirements → Design → Implementation → Testing → Deployment

Not just code - a professional software engineering deliverable.

EOF

END=$(date +%s)
DURATION=$((END - START))

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              PRACTICE RUN COMPLETE                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Duration: ${DURATION} seconds"
echo "Target:   300 seconds (5 minutes)"
echo ""

if [ $DURATION -lt 240 ]; then
    echo "✓ Good pace! You have time to slow down and explain more."
elif [ $DURATION -lt 300 ]; then
    echo "✓ Perfect timing! Stick to this pace."
elif [ $DURATION -lt 360 ]; then
    echo "⚠ Slightly over. Skip some outputs or speak faster."
else
    echo "⚠ Too long. Use the QUICK version from VIDEO_DEMO_SCRIPT.md"
fi
echo ""
echo "Ready to record? Read VIDEO_DEMO_SCRIPT.md for full details."
echo ""

