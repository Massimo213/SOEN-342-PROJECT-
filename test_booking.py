#!/usr/bin/env python3
"""
Test Suite for Booking System - Iteration 2

Comprehensive tests covering:
- Scenario 1: Family booking (4 travelers)
- Scenario 2: Solo traveler
- Edge cases and business rule violations
"""

from rail_network import RailNetwork, Itinerary, Leg, TrainRoute
from booking_system import BookingSystem, Client, generate_trip_id, generate_ticket_id
from datetime import datetime
import sys


def test_id_generation():
    """Test unique ID generation."""
    print("\n" + "="*80)
    print("TEST: ID Generation")
    print("="*80)
    
    # Trip IDs should be alphanumeric
    trip_ids = [generate_trip_id() for _ in range(5)]
    print(f"Generated Trip IDs: {trip_ids}")
    assert len(set(trip_ids)) == 5, "Trip IDs should be unique"
    assert all(tid.startswith("TRP-") for tid in trip_ids), "Trip IDs should have TRP- prefix"
    
    # Ticket IDs should be numeric
    ticket_ids = [generate_ticket_id() for _ in range(5)]
    print(f"Generated Ticket IDs: {ticket_ids}")
    assert len(set(ticket_ids)) == 5, "Ticket IDs should be unique"
    assert all(isinstance(tid, int) for tid in ticket_ids), "Ticket IDs should be integers"
    
    print("✓ ID generation tests passed")


def test_client_identity():
    """Test client identity and deduplication."""
    print("\n" + "="*80)
    print("TEST: Client Identity")
    print("="*80)
    
    # Same identity (last_name + id_number)
    client1 = Client("John", "Smith", "ABC123", 30)
    client2 = Client("John", "Smith", "ABC123", 31)  # Different age, same identity
    
    assert client1 == client2, "Clients with same last_name+id should be equal"
    assert hash(client1) == hash(client2), "Equal clients should have same hash"
    
    # Different identity
    client3 = Client("Jane", "Smith", "DEF456", 25)
    assert client1 != client3, "Different clients should not be equal"
    
    # Set deduplication
    clients = {client1, client2, client3}
    assert len(clients) == 2, "Set should deduplicate by identity"
    
    print("✓ Client identity tests passed")


def test_scenario_1_family_booking(rail_network: RailNetwork):
    """
    Scenario 1: Family of four books a trip.
    Expected:
    - Single trip with 4 reservations
    - 4 unique tickets
    - Trip and tickets have unique IDs
    """
    print("\n" + "="*80)
    print("SCENARIO 1: Family of Four")
    print("="*80)
    
    booking_system = BookingSystem()
    
    # Search for a connection
    connections = rail_network.search(
        departure_city="Paris",
        arrival_city="Berlin",
        max_stops=1,
        travel_class="second"
    )
    
    assert len(connections) > 0, "Should find connections"
    selected_connection = connections[0]
    
    print(f"Selected connection: {selected_connection.origin} → {selected_connection.destination}")
    print(f"Departure: {selected_connection.departure_time}")
    print(f"Arrival: {selected_connection.arrival_time}")
    
    # Family members
    family = [
        ("John", "Smith", "PASS001", 45),
        ("Jane", "Smith", "PASS002", 42),
        ("Emily", "Smith", "PASS003", 16),
        ("Michael", "Smith", "PASS004", 12)
    ]
    
    # Book trip
    trip = booking_system.book_trip(selected_connection, family)
    
    # Assertions
    assert trip.trip_id.startswith("TRP-"), "Trip ID should have correct format"
    assert trip.total_travelers() == 4, "Should have 4 travelers"
    assert len(trip.reservations) == 4, "Should have 4 reservations"
    
    # Check tickets
    ticket_ids = [res.ticket.ticket_id for res in trip.reservations]
    assert len(set(ticket_ids)) == 4, "All tickets should have unique IDs"
    
    # Check clients
    clients = trip.get_clients()
    assert len(clients) == 4, "Should have 4 clients"
    
    print(f"\n✓ Booked trip: {trip.trip_id}")
    print(f"  Travelers: {trip.total_travelers()}")
    print(f"  Tickets: {ticket_ids}")
    
    # Verify retrieval
    current, past = booking_system.get_trips_by_client("Smith", "PASS001")
    assert len(current) == 1, "Should find 1 current trip"
    assert current[0].trip_id == trip.trip_id, "Should retrieve same trip"
    
    print("✓ Scenario 1 passed")


def test_scenario_2_solo_traveler(rail_network: RailNetwork):
    """
    Scenario 2: Solo traveler books a trip.
    Expected:
    - Single trip with 1 reservation
    - 1 ticket
    """
    print("\n" + "="*80)
    print("SCENARIO 2: Solo Traveler")
    print("="*80)
    
    booking_system = BookingSystem()
    
    # Search for a connection
    connections = rail_network.search(
        departure_city="Amsterdam",
        arrival_city="Brussels",
        max_stops=0,
        travel_class="first"
    )
    
    assert len(connections) > 0, "Should find connections"
    selected_connection = connections[0]
    
    print(f"Selected connection: {selected_connection.origin} → {selected_connection.destination}")
    
    # Solo traveler
    traveler = [("Alice", "Johnson", "ID789", 28)]
    
    # Book trip
    trip = booking_system.book_trip(selected_connection, traveler)
    
    # Assertions
    assert trip.trip_id.startswith("TRP-"), "Trip ID should have correct format"
    assert trip.total_travelers() == 1, "Should have 1 traveler"
    assert len(trip.reservations) == 1, "Should have 1 reservation"
    
    ticket = trip.reservations[0].ticket
    assert isinstance(ticket.ticket_id, int), "Ticket ID should be integer"
    
    print(f"\n✓ Booked trip: {trip.trip_id}")
    print(f"  Traveler: {ticket.client.first_name} {ticket.client.last_name}")
    print(f"  Ticket: #{ticket.ticket_id}")
    
    print("✓ Scenario 2 passed")


def test_duplicate_booking_prevention(rail_network: RailNetwork):
    """
    Test business rule: Client cannot have multiple reservations for same connection.
    """
    print("\n" + "="*80)
    print("TEST: Duplicate Booking Prevention")
    print("="*80)
    
    booking_system = BookingSystem()
    
    connections = rail_network.search(
        departure_city="London",
        arrival_city="Paris",
        max_stops=1
    )
    
    assert len(connections) > 0, "Should find connections"
    connection = connections[0]
    
    # First booking
    traveler = [("Bob", "Brown", "ID999", 35)]
    trip1 = booking_system.book_trip(connection, traveler)
    print(f"First booking: {trip1.trip_id}")
    
    # Attempt duplicate booking
    try:
        trip2 = booking_system.book_trip(connection, traveler)
        assert False, "Should have raised ValueError for duplicate booking"
    except ValueError as e:
        print(f"✓ Duplicate prevented: {e}")
    
    print("✓ Duplicate booking prevention test passed")


def test_duplicate_travelers_in_trip(rail_network: RailNetwork):
    """
    Test: Cannot book same traveler twice in one trip.
    """
    print("\n" + "="*80)
    print("TEST: Duplicate Travelers in Single Trip")
    print("="*80)
    
    booking_system = BookingSystem()
    
    # Find any connection that works
    connections = rail_network.search(
        departure_city="Paris",
        arrival_city="Amsterdam",
        max_stops=1
    )
    
    assert len(connections) > 0, "Should find connections"
    connection = connections[0]
    
    # Try to book same person twice
    travelers = [
        ("Charlie", "Davis", "ID555", 40),
        ("Charlie", "Davis", "ID555", 40)  # Duplicate
    ]
    
    try:
        trip = booking_system.book_trip(connection, travelers)
        assert False, "Should have raised ValueError for duplicate traveler"
    except ValueError as e:
        print(f"✓ Duplicate prevented: {e}")
    
    print("✓ Duplicate travelers test passed")


def test_view_multiple_trips(rail_network: RailNetwork):
    """
    Test: Client can view all their trips.
    """
    print("\n" + "="*80)
    print("TEST: View Multiple Trips")
    print("="*80)
    
    booking_system = BookingSystem()
    
    # Book multiple trips for same client
    connections = rail_network.search(
        departure_city="Rome",
        arrival_city="Milan",
        max_stops=1
    )
    
    assert len(connections) >= 2, "Need at least 2 connections for test"
    
    traveler = [("Diana", "Wilson", "ID777", 33)]
    
    trip1 = booking_system.book_trip(connections[0], traveler)
    trip2 = booking_system.book_trip(connections[1], traveler)
    
    print(f"Booked trips: {trip1.trip_id}, {trip2.trip_id}")
    
    # Retrieve trips
    current, past = booking_system.get_trips_by_client("Wilson", "ID777")
    
    assert len(current) == 2, "Should have 2 current trips"
    trip_ids = {t.trip_id for t in current}
    assert trip1.trip_id in trip_ids, "Should find first trip"
    assert trip2.trip_id in trip_ids, "Should find second trip"
    
    print(f"✓ Retrieved {len(current)} trips for Diana Wilson")
    print("✓ View multiple trips test passed")


def test_validation_errors():
    """
    Test validation and error handling.
    """
    print("\n" + "="*80)
    print("TEST: Validation Errors")
    print("="*80)
    
    # Invalid age
    try:
        client = Client("Test", "User", "ID123", -5)
        assert False, "Should reject negative age"
    except ValueError as e:
        print(f"✓ Negative age rejected: {e}")
    
    # Empty name
    try:
        client = Client("", "User", "ID123", 25)
        assert False, "Should reject empty name"
    except ValueError as e:
        print(f"✓ Empty name rejected: {e}")
    
    # Empty ID
    try:
        client = Client("Test", "User", "", 25)
        assert False, "Should reject empty ID"
    except ValueError as e:
        print(f"✓ Empty ID rejected: {e}")
    
    print("✓ Validation tests passed")


def run_all_tests():
    """Run all test scenarios."""
    print("\n" + "="*80)
    print("BOOKING SYSTEM TEST SUITE - ITERATION 2")
    print("="*80)
    
    # Load rail network
    print("\nLoading rail network...")
    rail_network = RailNetwork.from_csv("eu_rail_network.csv")
    print(f"Loaded {len(rail_network.routes)} routes")
    
    # Run tests
    try:
        test_id_generation()
        test_client_identity()
        test_validation_errors()
        test_scenario_1_family_booking(rail_network)
        test_scenario_2_solo_traveler(rail_network)
        test_duplicate_booking_prevention(rail_network)
        test_duplicate_travelers_in_trip(rail_network)
        test_view_multiple_trips(rail_network)
        
        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED")
        print("="*80 + "\n")
        
        return 0
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

