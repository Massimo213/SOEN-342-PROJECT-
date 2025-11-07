#!/usr/bin/env python3
"""
Test Suite - Iteration 3

Tests for database persistence, layover validation, and numeric trip IDs.

Run with: python3 test_iteration3.py
"""

import unittest
import os
from database import Database
from booking_system_v3 import BookingSystem, Client, Trip
from rail_network import RailNetwork, Itinerary, Leg, TrainRoute
from layover_validator import LayoverValidator


class TestDatabase(unittest.TestCase):
    """Test database operations."""
    
    def setUp(self):
        """Create in-memory database for each test."""
        self.db = Database(":memory:")
    
    def test_schema_creation(self):
        """Verify all tables created."""
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            tables = [row['name'] for row in cursor.fetchall()]
        
        expected = ['clients', 'routes', 'tickets', 'trip_legs', 'trips']
        # sqlite_sequence is auto-created for AUTOINCREMENT, filter it out
        tables = [t for t in tables if t != 'sqlite_sequence']
        self.assertEqual(tables, expected)
    
    def test_load_routes_from_csv(self):
        """Test CSV loading."""
        count = self.db.load_routes_from_csv("eu_rail_network.csv")
        self.assertGreater(count, 0, "Should load at least one route")
        
        # Verify routes in database
        routes = self.db.get_all_routes()
        self.assertEqual(len(routes), count)
    
    def test_client_deduplication(self):
        """Test UNIQUE constraint on (last_name, id_number)."""
        # Create client twice
        client_id_1 = self.db.get_or_create_client("John", "Smith", "PASS001", 45)
        client_id_2 = self.db.get_or_create_client("John", "Smith", "PASS001", 45)
        
        # Should return same client_id
        self.assertEqual(client_id_1, client_id_2)
    
    def test_trip_auto_increment(self):
        """Test trip_id auto-increments."""
        trip_id_1 = self.db.create_trip("Paris", "Berlin", "08:30", "16:45")
        trip_id_2 = self.db.create_trip("Amsterdam", "Brussels", "10:15", "12:30")
        
        self.assertIsInstance(trip_id_1, int)
        self.assertIsInstance(trip_id_2, int)
        self.assertNotEqual(trip_id_1, trip_id_2)
    
    def test_foreign_key_constraints(self):
        """Test foreign keys enforced."""
        # Try to create ticket for non-existent trip
        with self.assertRaises(Exception):
            with self.db.connection() as conn:
                conn.execute("""
                    INSERT INTO tickets (client_id, trip_id, issue_timestamp)
                    VALUES (999, 999, '2025-11-07 12:00:00')
                """)
    
    def test_cascade_delete(self):
        """Test CASCADE DELETE for trip → tickets."""
        # Create trip with ticket
        trip_id = self.db.create_trip("Paris", "Berlin", "08:30", "16:45")
        client_id = self.db.get_or_create_client("John", "Smith", "PASS001", 45)
        ticket_id = self.db.create_ticket(client_id, trip_id)
        
        # Delete trip
        with self.db.connection() as conn:
            conn.execute("DELETE FROM trips WHERE trip_id = ?", (trip_id,))
        
        # Ticket should be deleted too
        tickets = self.db.get_tickets_for_trip(trip_id)
        self.assertEqual(len(tickets), 0)
    
    def test_statistics(self):
        """Test database statistics."""
        stats = self.db.get_statistics()
        
        self.assertIn('routes', stats)
        self.assertIn('clients', stats)
        self.assertIn('trips', stats)
        self.assertIn('tickets', stats)
        self.assertIsInstance(stats['routes'], int)


class TestLayoverValidator(unittest.TestCase):
    """Test layover validation logic."""
    
    def test_daytime_acceptable_layover(self):
        """Test valid daytime layover (60 minutes)."""
        # 10:00 → 11:00 (60 min)
        is_valid, reason = LayoverValidator.is_layover_acceptable(
            arrival_minutes=10 * 60,
            departure_minutes=11 * 60,
            policy="strict"
        )
        self.assertTrue(is_valid)
        self.assertEqual(reason, "OK")
    
    def test_daytime_too_long(self):
        """Test rejected daytime layover (3 hours)."""
        # 10:00 → 13:00 (180 min) - exceeds 120 min limit
        is_valid, reason = LayoverValidator.is_layover_acceptable(
            arrival_minutes=10 * 60,
            departure_minutes=13 * 60,
            policy="strict"
        )
        self.assertFalse(is_valid)
        self.assertIn("too long", reason)
    
    def test_daytime_too_short(self):
        """Test rejected short layover (10 minutes)."""
        # 10:00 → 10:10 (10 min) - below 15 min minimum
        is_valid, reason = LayoverValidator.is_layover_acceptable(
            arrival_minutes=10 * 60,
            departure_minutes=10 * 60 + 10,
            policy="strict"
        )
        self.assertFalse(is_valid)
        self.assertIn("too short", reason)
    
    def test_after_hours_acceptable(self):
        """Test valid after-hours layover (25 minutes)."""
        # 23:00 → 23:25 (25 min)
        is_valid, reason = LayoverValidator.is_layover_acceptable(
            arrival_minutes=23 * 60,
            departure_minutes=23 * 60 + 25,
            policy="strict"
        )
        self.assertTrue(is_valid)
    
    def test_after_hours_too_long(self):
        """Test rejected after-hours layover (45 minutes)."""
        # 23:00 → 23:45 (45 min) - exceeds 30 min limit
        is_valid, reason = LayoverValidator.is_layover_acceptable(
            arrival_minutes=23 * 60,
            departure_minutes=23 * 60 + 45,
            policy="strict"
        )
        self.assertFalse(is_valid)
        self.assertIn("too long", reason)
        self.assertIn("after-hours", reason)
    
    def test_lenient_policy(self):
        """Test lenient policy allows longer layovers."""
        # 10:00 → 12:30 (150 min) - rejected in strict, OK in lenient
        is_valid_strict, _ = LayoverValidator.is_layover_acceptable(
            10 * 60, 12 * 60 + 30, "strict"
        )
        is_valid_lenient, _ = LayoverValidator.is_layover_acceptable(
            10 * 60, 12 * 60 + 30, "lenient"
        )
        
        self.assertFalse(is_valid_strict)
        self.assertTrue(is_valid_lenient)
    
    def test_multi_stop_validation(self):
        """Test multi-stop connection validation."""
        # Two transfers: both valid
        leg_times = [
            (10 * 60, 11 * 60),  # Transfer 1: 60 min
            (14 * 60, 15 * 60),  # Transfer 2: 60 min
        ]
        is_valid, reason = LayoverValidator.validate_multi_stop_connection(
            leg_times, "strict"
        )
        self.assertTrue(is_valid)
    
    def test_multi_stop_one_invalid(self):
        """Test multi-stop with one invalid transfer."""
        leg_times = [
            (10 * 60, 11 * 60),  # Transfer 1: 60 min - OK
            (14 * 60, 17 * 60),  # Transfer 2: 180 min - TOO LONG
        ]
        is_valid, reason = LayoverValidator.validate_multi_stop_connection(
            leg_times, "strict"
        )
        self.assertFalse(is_valid)
        self.assertIn("Transfer 2", reason)


class TestRailNetworkWithLayover(unittest.TestCase):
    """Test RailNetwork search with layover validation."""
    
    def setUp(self):
        """Create network with test routes."""
        self.routes = [
            # Direct route
            TrainRoute("R001", "Paris", "Berlin", "08:30", "16:45", 
                      "ICE", "Daily", 150.0, 89.0),
            
            # 1-stop with good layover (60 min)
            TrainRoute("R002", "Paris", "Frankfurt", "08:00", "12:00", 
                      "ICE", "Daily", 100.0, 60.0),
            TrainRoute("R003", "Frankfurt", "Berlin", "13:00", "17:00", 
                      "ICE", "Daily", 80.0, 50.0),
            
            # 1-stop with bad layover (3 hours)
            TrainRoute("R004", "Paris", "Munich", "09:00", "14:00", 
                      "ICE", "Daily", 120.0, 70.0),
            TrainRoute("R005", "Munich", "Berlin", "17:00", "21:00", 
                      "ICE", "Daily", 90.0, 55.0),
        ]
        self.network = RailNetwork(self.routes)
    
    def test_search_with_strict_policy(self):
        """Test search rejects bad layovers."""
        results = self.network.search(
            departure_city="Paris",
            arrival_city="Berlin",
            max_stops=1,
            layover_policy="strict"
        )
        
        # Should include direct + 1-stop with 60min layover
        # Should exclude 1-stop with 180min layover
        self.assertGreaterEqual(len(results), 2)
        
        # Verify the 3-hour layover connection is not included
        for conn in results:
            if len(conn.legs) == 2:
                route_ids = [leg.route.route_id for leg in conn.legs]
                # R004 → R005 should be excluded
                self.assertNotEqual(route_ids, ["R004", "R005"])
    
    def test_search_with_lenient_policy(self):
        """Test lenient policy allows longer layovers."""
        strict_results = self.network.search(
            departure_city="Paris",
            arrival_city="Berlin",
            max_stops=1,
            layover_policy="strict"
        )
        
        lenient_results = self.network.search(
            departure_city="Paris",
            arrival_city="Berlin",
            max_stops=1,
            layover_policy="lenient"
        )
        
        # Lenient should return same or more results
        self.assertGreaterEqual(len(lenient_results), len(strict_results))


class TestBookingSystemV3(unittest.TestCase):
    """Test database-backed booking system."""
    
    def setUp(self):
        """Create in-memory database and booking system."""
        self.db = Database(":memory:")
        self.db.load_routes_from_csv("eu_rail_network.csv")
        self.booking_system = BookingSystem(self.db)
        
        # Create test connection
        self.network = RailNetwork.from_csv("eu_rail_network.csv")
        connections = self.network.search(
            departure_city="Paris",
            arrival_city="Berlin",
            max_stops=0
        )
        self.test_connection = connections[0] if connections else None
    
    def test_book_single_traveler(self):
        """Test booking for one traveler."""
        if not self.test_connection:
            self.skipTest("No test connection available")
        
        trip = self.booking_system.book_trip(
            self.test_connection,
            [("John", "Smith", "PASS001", 45)]
        )
        
        self.assertIsInstance(trip.trip_id, int, "Trip ID should be numeric")
        self.assertEqual(trip.total_travelers(), 1)
        self.assertGreater(trip.trip_id, 0)
    
    def test_book_multiple_travelers(self):
        """Test family booking."""
        if not self.test_connection:
            self.skipTest("No test connection available")
        
        trip = self.booking_system.book_trip(
            self.test_connection,
            [
                ("John", "Smith", "PASS001", 45),
                ("Jane", "Smith", "PASS002", 42),
                ("Emily", "Smith", "PASS003", 16)
            ]
        )
        
        self.assertIsInstance(trip.trip_id, int)
        self.assertEqual(trip.total_travelers(), 3)
        self.assertEqual(len(trip.reservations), 3)
        
        # Verify all tickets have unique IDs
        ticket_ids = [res.ticket.ticket_id for res in trip.reservations]
        self.assertEqual(len(ticket_ids), len(set(ticket_ids)))
    
    def test_duplicate_booking_prevention(self):
        """Test client cannot book same connection twice."""
        if not self.test_connection:
            self.skipTest("No test connection available")
        
        # First booking
        self.booking_system.book_trip(
            self.test_connection,
            [("Alice", "Johnson", "ID789", 28)]
        )
        
        # Second booking should fail
        with self.assertRaises(ValueError) as cm:
            self.booking_system.book_trip(
                self.test_connection,
                [("Alice", "Johnson", "ID789", 28)]
            )
        
        self.assertIn("already has a reservation", str(cm.exception))
    
    def test_duplicate_traveler_in_booking(self):
        """Test cannot add same person twice in one booking."""
        if not self.test_connection:
            self.skipTest("No test connection available")
        
        with self.assertRaises(ValueError) as cm:
            self.booking_system.book_trip(
                self.test_connection,
                [
                    ("Bob", "Brown", "PASS999", 30),
                    ("Bob", "Brown", "PASS999", 30)  # Duplicate
                ]
            )
        
        self.assertIn("Duplicate client", str(cm.exception))
    
    def test_view_trips_by_client(self):
        """Test retrieving trips by client credentials."""
        if not self.test_connection:
            self.skipTest("No test connection available")
        
        # Book trip
        trip = self.booking_system.book_trip(
            self.test_connection,
            [("Charlie", "Davis", "STATE123", 35)]
        )
        
        # Retrieve trips
        current, past = self.booking_system.get_trips_by_client("Davis", "STATE123")
        
        self.assertEqual(len(current), 1)
        self.assertEqual(len(past), 0)
        self.assertEqual(current[0].trip_id, trip.trip_id)
    
    def test_get_trip_by_id(self):
        """Test retrieving trip by numeric ID."""
        if not self.test_connection:
            self.skipTest("No test connection available")
        
        trip = self.booking_system.book_trip(
            self.test_connection,
            [("David", "Evans", "PASS456", 50)]
        )
        
        retrieved = self.booking_system.get_trip_by_id(trip.trip_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.trip_id, trip.trip_id)
        self.assertEqual(retrieved.total_travelers(), 1)
    
    def test_persistence_across_sessions(self):
        """Test data persists across BookingSystem instances."""
        if not self.test_connection:
            self.skipTest("No test connection available")
        
        # Create DB file (not in-memory)
        db_path = "test_persistence.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        
        try:
            # Session 1: Create booking
            db1 = Database(db_path)
            db1.load_routes_from_csv("eu_rail_network.csv")
            bs1 = BookingSystem(db1)
            
            network = RailNetwork.from_csv("eu_rail_network.csv")
            conn = network.search(departure_city="Paris", arrival_city="Berlin", max_stops=0)[0]
            
            trip = bs1.book_trip(conn, [("Test", "User", "TEST001", 30)])
            trip_id = trip.trip_id
            
            # Session 2: Retrieve booking
            db2 = Database(db_path)
            bs2 = BookingSystem(db2)
            
            retrieved = bs2.get_trip_by_id(trip_id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.trip_id, trip_id)
        
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""
    
    def test_full_booking_workflow(self):
        """Test complete workflow: search → book → view."""
        # Setup
        db = Database(":memory:")
        db.load_routes_from_csv("eu_rail_network.csv")
        network = RailNetwork.from_csv("eu_rail_network.csv")
        booking_system = BookingSystem(db)
        
        # 1. Search for connections
        connections = network.search(
            departure_city="Amsterdam",
            arrival_city="Brussels",
            max_stops=1,
            layover_policy="strict"
        )
        self.assertGreater(len(connections), 0, "Should find connections")
        
        # 2. Book first connection
        trip = booking_system.book_trip(
            connections[0],
            [("Integration", "Test", "INT001", 25)]
        )
        self.assertIsInstance(trip.trip_id, int)
        
        # 3. View trips
        current, past = booking_system.get_trips_by_client("Test", "INT001")
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0].trip_id, trip.trip_id)
        
        # 4. Verify cannot book same connection again
        with self.assertRaises(ValueError):
            booking_system.book_trip(
                connections[0],
                [("Integration", "Test", "INT001", 25)]
            )


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestLayoverValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestRailNetworkWithLayover))
    suite.addTests(loader.loadTestsFromTestCase(TestBookingSystemV3))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)

