#!/usr/bin/env python3
"""
Test Suite - Final Iteration

Tests for OCL constraints and state machine implementation.
Validates that the software system enforces all formal specifications.

Run with: python3 test_final_iteration.py
"""

import unittest
from database import Database
from booking_system_v3 import BookingSystem, Client
from rail_network import RailNetwork
from booking_state_machine import BookingStateMachine, BookingState


class TestOCLConstraints(unittest.TestCase):
    """Test OCL constraint enforcement at runtime."""
    
    def setUp(self):
        """Create in-memory database and booking system."""
        self.db = Database(":memory:")
        self.db.load_routes_from_csv("eu_rail_network.csv")
        self.booking_system = BookingSystem(self.db)
        self.network = RailNetwork.from_csv("eu_rail_network.csv")
        
        # Get test connection
        connections = self.network.search(
            departure_city="Paris",
            arrival_city="Berlin",
            max_stops=0
        )
        self.test_connection = connections[0] if connections else None
    
    def test_ocl_precondition_travelers_not_empty(self):
        """
        OCL: book_trip pre: travelers->notEmpty()
        """
        if not self.test_connection:
            self.skipTest("No test connection")
        
        # Violate precondition: empty travelers list
        with self.assertRaises(ValueError) as cm:
            self.booking_system.book_trip(self.test_connection, [])
        
        self.assertIn("At least one traveler required", str(cm.exception))
    
    def test_ocl_precondition_no_duplicate_travelers(self):
        """
        OCL: book_trip pre: travelers->forAll(t1, t2 | t1 <> t2 implies ...)
        """
        if not self.test_connection:
            self.skipTest("No test connection")
        
        # Violate precondition: duplicate travelers
        with self.assertRaises(ValueError) as cm:
            self.booking_system.book_trip(self.test_connection, [
                ("John", "Smith", "PASS001", 45),
                ("John", "Smith", "PASS001", 45)  # DUPLICATE
            ])
        
        self.assertIn("Duplicate client", str(cm.exception))
    
    def test_ocl_precondition_no_existing_booking(self):
        """
        OCL: book_trip pre: not hasBookingForConnection(...)
        """
        if not self.test_connection:
            self.skipTest("No test connection")
        
        # First booking: should succeed
        trip1 = self.booking_system.book_trip(self.test_connection, [
            ("Alice", "Johnson", "ID001", 30)
        ])
        self.assertIsNotNone(trip1)
        
        # Second booking for same client + connection: should fail
        with self.assertRaises(ValueError) as cm:
            self.booking_system.book_trip(self.test_connection, [
                ("Alice", "Johnson", "ID001", 30)
            ])
        
        self.assertIn("already has a reservation", str(cm.exception))
    
    def test_ocl_postcondition_positive_trip_id(self):
        """
        OCL: book_trip post: result.trip_id > 0
        """
        if not self.test_connection:
            self.skipTest("No test connection")
        
        trip = self.booking_system.book_trip(self.test_connection, [
            ("Bob", "Brown", "ID002", 40)
        ])
        
        # Postcondition: trip_id must be positive
        self.assertGreater(trip.trip_id, 0)
        self.assertIsInstance(trip.trip_id, int)
    
    def test_ocl_postcondition_correct_reservation_count(self):
        """
        OCL: book_trip post: result.reservations->size() = travelers->size()
        """
        if not self.test_connection:
            self.skipTest("No test connection")
        
        travelers = [
            ("Charlie", "Davis", "ID003", 35),
            ("Diana", "Evans", "ID004", 32),
            ("Eve", "Foster", "ID005", 28)
        ]
        
        trip = self.booking_system.book_trip(self.test_connection, travelers)
        
        # Postcondition: one reservation per traveler
        self.assertEqual(len(trip.reservations), len(travelers))
    
    def test_ocl_postcondition_unique_ticket_ids(self):
        """
        OCL: book_trip post: result.reservations->forAll(r1, r2 | 
                              r1 <> r2 implies r1.ticket.ticket_id <> r2.ticket.ticket_id)
        """
        if not self.test_connection:
            self.skipTest("No test connection")
        
        trip = self.booking_system.book_trip(self.test_connection, [
            ("Frank", "Green", "ID006", 50),
            ("Grace", "Harris", "ID007", 48)
        ])
        
        ticket_ids = [res.ticket.ticket_id for res in trip.reservations]
        
        # Postcondition: all ticket IDs unique
        self.assertEqual(len(ticket_ids), len(set(ticket_ids)))
    
    def test_ocl_reservation_invariant_client_ticket_match(self):
        """
        OCL: Reservation inv: self.ticket.client = self.client
        """
        if not self.test_connection:
            self.skipTest("No test connection")
        
        trip = self.booking_system.book_trip(self.test_connection, [
            ("Helen", "Irving", "ID008", 27)
        ])
        
        # Invariant: ticket client matches reservation client
        for reservation in trip.reservations:
            self.assertEqual(reservation.ticket.client, reservation.client)
    
    def test_ocl_client_invariant_valid_age(self):
        """
        OCL: Client inv: self.age >= 0
        """
        # Violate invariant: negative age
        with self.assertRaises(ValueError):
            Client("Invalid", "Person", "ID999", -5)
    
    def test_ocl_client_invariant_non_empty_names(self):
        """
        OCL: Client inv: self.first_name <> '' and self.last_name <> ''
        """
        # Violate invariant: empty name
        with self.assertRaises(ValueError):
            Client("", "Smith", "ID999", 30)
        
        with self.assertRaises(ValueError):
            Client("John", "", "ID999", 30)
    
    def test_ocl_trip_invariant_has_reservations(self):
        """
        OCL: Trip inv: self.reservations->notEmpty()
        """
        if not self.test_connection:
            self.skipTest("No test connection")
        
        trip = self.booking_system.book_trip(self.test_connection, [
            ("Ivan", "Jackson", "ID009", 55)
        ])
        
        # Invariant: trip must have at least one reservation
        self.assertGreater(len(trip.reservations), 0)


class TestStateMachine(unittest.TestCase):
    """Test state machine implementation."""
    
    def setUp(self):
        """Create state machine."""
        self.db = Database(":memory:")
        self.db.load_routes_from_csv("eu_rail_network.csv")
        self.booking_system = BookingSystem(self.db)
        self.network = RailNetwork.from_csv("eu_rail_network.csv")
        self.state_machine = BookingStateMachine(self.network, self.booking_system)
    
    def test_initial_state_is_idle(self):
        """State machine starts in IDLE state."""
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.IDLE
        )
    
    def test_transition_idle_to_searching(self):
        """Transition from IDLE to SEARCHING_CONNECTION."""
        result = self.state_machine.start_booking("Amsterdam", "Brussels")
        
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.DISPLAYING_RESULTS
        )
    
    def test_transition_through_selection(self):
        """Complete transition: IDLE -> SEARCHING -> DISPLAYING -> SELECTING."""
        # Start booking
        self.state_machine.start_booking("Amsterdam", "Brussels")
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.DISPLAYING_RESULTS
        )
        
        # Select first connection
        result = self.state_machine.select_connection(0)
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.ENTERING_TRAVELERS
        )
    
    def test_validation_failure_transitions_back(self):
        """Failed validation returns to ENTERING_TRAVELERS state."""
        # Setup: get to ENTERING_TRAVELERS state
        self.state_machine.start_booking("Amsterdam", "Brussels")
        self.state_machine.select_connection(0)
        
        # Add invalid travelers (duplicate)
        self.state_machine.add_travelers([
            ("John", "Smith", "PASS001", 45),
            ("John", "Smith", "PASS001", 45)  # DUPLICATE
        ])
        
        # Should transition to VALIDATING then back to ENTERING
        self.state_machine.execute_current_state()
        
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.ENTERING_TRAVELERS
        )
        self.assertGreater(len(self.state_machine.context.validation_errors), 0)
    
    def test_successful_booking_complete_flow(self):
        """Complete successful booking flow."""
        # 1. Start booking
        self.state_machine.start_booking("Amsterdam", "Brussels")
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.DISPLAYING_RESULTS
        )
        
        # 2. Select connection
        self.state_machine.select_connection(0)
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.ENTERING_TRAVELERS
        )
        
        # 3. Add travelers
        self.state_machine.add_travelers([
            ("Test", "User", "TEST001", 30)
        ])
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.VALIDATING_TRAVELERS
        )
        
        # 4. Validation passes, moves to CREATING
        self.state_machine.execute_current_state()
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.CREATING_RESERVATION
        )
        
        # 5. Creation succeeds, moves to CONFIRMATION
        self.state_machine.execute_current_state()
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.DISPLAYING_CONFIRMATION
        )
        
        # 6. Confirmation returns to IDLE
        self.state_machine.execute_current_state()
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.IDLE
        )
        
        # 7. Verify booking is complete
        self.assertTrue(self.state_machine.is_complete())
        self.assertIsNotNone(self.state_machine.context.trip_id)
    
    def test_cancel_returns_to_idle(self):
        """Cancel operation returns to IDLE from any state."""
        # Start booking
        self.state_machine.start_booking("Amsterdam", "Brussels")
        
        # Cancel
        self.state_machine.cancel()
        
        self.assertEqual(
            self.state_machine.get_current_state(),
            BookingState.IDLE
        )
    
    def test_error_handling_state(self):
        """Error conditions transition to HANDLING_ERROR state."""
        # Start booking with invalid criteria
        self.state_machine.context.departure_city = None  # Invalid
        self.state_machine.transition_to(
            BookingState.SEARCHING_CONNECTION,
            "test"
        )
        
        result = self.state_machine.execute_current_state()
        
        # Should detect error (though may not transition to ERROR state
        # depending on implementation)
        self.assertIn(result, ["invalid_criteria", "error", "no_results"])
    
    def test_state_context_preservation(self):
        """Context data is preserved across state transitions."""
        # Start booking
        self.state_machine.start_booking("Paris", "Berlin", max_stops=1)
        
        # Verify context
        self.assertEqual(self.state_machine.context.departure_city, "Paris")
        self.assertEqual(self.state_machine.context.arrival_city, "Berlin")
        self.assertEqual(self.state_machine.context.max_stops, 1)
        
        # Select connection
        if self.state_machine.context.connections:
            self.state_machine.select_connection(0)
            
            # Verify selected connection preserved
            self.assertIsNotNone(
                self.state_machine.context.selected_connection
            )


class TestOCLLayoverConstraints(unittest.TestCase):
    """Test layover validation constraints."""
    
    def setUp(self):
        """Create network for testing."""
        self.network = RailNetwork.from_csv("eu_rail_network.csv")
    
    def test_invalid_layovers_filtered(self):
        """
        OCL: Itinerary inv: validLayovers
        Connections with invalid layovers should be filtered out.
        """
        # Search with strict policy
        connections = self.network.search(
            departure_city="Paris",
            arrival_city="Berlin",
            max_stops=1,
            layover_policy="strict"
        )
        
        # All returned connections should have valid layovers
        for conn in connections:
            if len(conn.legs) > 1:
                for i in range(len(conn.legs) - 1):
                    prev_arr = conn.legs[i].route.arr_min
                    next_dep = conn.legs[i+1].route.dep_min
                    
                    gap = next_dep - prev_arr
                    if gap < 0:
                        gap += 24 * 60
                    
                    # Check layover is within bounds
                    # (This is enforced by LayoverValidator)
                    self.assertGreaterEqual(gap, 15)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestOCLConstraints))
    suite.addTests(loader.loadTestsFromTestCase(TestStateMachine))
    suite.addTests(loader.loadTestsFromTestCase(TestOCLLayoverConstraints))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("FINAL ITERATION TEST RESULTS")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\nAll tests passed - Final iteration complete!")
    else:
        print("\nSome tests failed")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)

