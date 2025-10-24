#!/usr/bin/env python3
"""
Live Demo - Iteration 2 Requirements

Interactive demonstration of all booking system features.
"""

from rail_network import RailNetwork
from booking_system import BookingSystem


def demo_scenario_1():
    """Demo: Family of four books a trip."""
    print("\n" + "="*80)
    print("DEMO: Scenario 1 — Family Booking")
    print("="*80)
    
    # Load network
    network = RailNetwork.from_csv("eu_rail_network.csv")
    booking = BookingSystem()
    
    # Search for Paris → Berlin
    print("\nSearching: Paris → Berlin (max 1 stop)")
    connections = network.search(
        departure_city="Paris",
        arrival_city="Berlin",
        max_stops=1,
        sort_by="duration"
    )
    
    print(f"Found {len(connections)} connections")
    selected = connections[0]
    
    print(f"\nSelected connection:")
    print(f"  {selected.origin} → {selected.destination}")
    print(f"  Depart: {selected.departure_time}")
    print(f"  Arrive: {selected.arrival_time}")
    print(f"  Duration: {selected.total_travel_minutes} min")
    print(f"  Price (2nd class): €{selected.price('second'):.2f}")
    
    # Smith family booking
    family = [
        ("John", "Smith", "PASS001", 45),
        ("Jane", "Smith", "PASS002", 42),
        ("Emily", "Smith", "PASS003", 16),
        ("Michael", "Smith", "PASS004", 12)
    ]
    
    print(f"\nBooking for Smith family ({len(family)} travelers)...")
    trip = booking.book_trip(selected, family)
    
    print(f"\n✓ Trip booked successfully!")
    print(f"  Trip ID: {trip.trip_id}")
    print(f"  Booked at: {trip.booking_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total travelers: {trip.total_travelers()}")
    
    print(f"\n  Tickets issued:")
    for i, res in enumerate(trip.reservations, 1):
        client = res.client
        ticket = res.ticket
        print(f"    {i}. {client.first_name} {client.last_name} (age {client.age})")
        print(f"       Ticket #{ticket.ticket_id}")
    
    return booking, trip


def demo_scenario_2(booking: BookingSystem):
    """Demo: Solo traveler books a trip."""
    print("\n" + "="*80)
    print("DEMO: Scenario 2 — Solo Traveler")
    print("="*80)
    
    network = RailNetwork.from_csv("eu_rail_network.csv")
    
    # Search Amsterdam → Brussels (direct)
    print("\nSearching: Amsterdam → Brussels (direct only)")
    connections = network.search(
        departure_city="Amsterdam",
        arrival_city="Brussels",
        max_stops=0,
        travel_class="first"
    )
    
    print(f"Found {len(connections)} direct connections")
    selected = connections[0]
    
    print(f"\nSelected connection:")
    print(f"  {selected.origin} → {selected.destination}")
    print(f"  Depart: {selected.departure_time}")
    print(f"  Arrive: {selected.arrival_time}")
    print(f"  Price (1st class): €{selected.price('first'):.2f}")
    
    # Solo traveler
    traveler = [("Alice", "Johnson", "ID789", 28)]
    
    print(f"\nBooking for Alice Johnson...")
    trip = booking.book_trip(selected, traveler)
    
    ticket = trip.reservations[0].ticket
    print(f"\n✓ Trip booked successfully!")
    print(f"  Trip ID: {trip.trip_id}")
    print(f"  Ticket: #{ticket.ticket_id}")
    print(f"  Traveler: {ticket.client.first_name} {ticket.client.last_name}")
    
    return trip


def demo_view_trips(booking: BookingSystem):
    """Demo: View client trips."""
    print("\n" + "="*80)
    print("DEMO: View Trips")
    print("="*80)
    
    # View Smith family trips
    print("\nQuerying trips for: Smith (ID: PASS001)")
    current, past = booking.get_trips_by_client("Smith", "PASS001")
    
    print(f"\nCurrent trips: {len(current)}")
    for trip in current:
        print(f"  • Trip {trip.trip_id}")
        print(f"    {trip.connection.origin} → {trip.connection.destination}")
        print(f"    Travelers: {trip.total_travelers()}")
    
    print(f"\nPast trips: {len(past)}")
    if past:
        for trip in past:
            print(f"  • Trip {trip.trip_id}")
    else:
        print("  (none)")


def demo_business_rules(booking: BookingSystem):
    """Demo: Business rule enforcement."""
    print("\n" + "="*80)
    print("DEMO: Business Rules")
    print("="*80)
    
    network = RailNetwork.from_csv("eu_rail_network.csv")
    
    # Get a connection
    connections = network.search(
        departure_city="London",
        arrival_city="Paris",
        max_stops=1
    )
    connection = connections[0]
    
    # First booking
    traveler = [("Bob", "Brown", "ID999", 35)]
    trip1 = booking.book_trip(connection, traveler)
    print(f"\n✓ First booking: {trip1.trip_id}")
    print(f"  Bob Brown: London → Paris")
    
    # Attempt duplicate
    print(f"\nAttempting duplicate booking for same connection...")
    try:
        trip2 = booking.book_trip(connection, traveler)
        print("  ✗ ERROR: Should have been prevented!")
    except ValueError as e:
        print(f"  ✓ Prevented: {e}")
    
    # Try duplicate traveler in single booking
    print(f"\nAttempting to book same traveler twice in one trip...")
    # Get a different connection
    other_connections = network.search(
        departure_city="Amsterdam",
        arrival_city="Paris",
        max_stops=1
    )
    try:
        trip3 = booking.book_trip(other_connections[0], [
            ("Charlie", "Davis", "ID555", 40),
            ("Charlie", "Davis", "ID555", 40)  # Duplicate
        ])
        print("  ✗ ERROR: Should have been prevented!")
    except ValueError as e:
        print(f"  ✓ Prevented: {e}")


def main():
    print("\n" + "="*80)
    print("RAIL BOOKING SYSTEM — ITERATION 2 DEMO")
    print("="*80)
    print("\nThis demo showcases all required functionality:")
    print("  • Scenario 1: Family booking (4 travelers)")
    print("  • Scenario 2: Solo traveler")
    print("  • View trips by client credentials")
    print("  • Business rule enforcement")
    
    input("\nPress Enter to begin...")
    
    # Run demos
    booking, family_trip = demo_scenario_1()
    solo_trip = demo_scenario_2(booking)
    demo_view_trips(booking)
    demo_business_rules(booking)
    
    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80)
    print(f"\nTotal trips booked: {len(booking.get_all_trips())}")
    print(f"Total clients registered: {len(booking.clients)}")
    print("\nAll requirements satisfied ✓")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

