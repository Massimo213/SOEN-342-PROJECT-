"""
Booking State Machine - Final Iteration

Implementation of the state machine for "Book a Trip" use case.
This is a production implementation of the UML state machine diagram.

Design Pattern: State Pattern
- Each state is a class
- State transitions are explicit
- Supports rollback and error handling
"""

from __future__ import annotations
from enum import Enum, auto
from typing import Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime


class BookingState(Enum):
    """Enumeration of all possible booking states."""
    IDLE = auto()
    SEARCHING_CONNECTION = auto()
    DISPLAYING_RESULTS = auto()
    SELECTING_CONNECTION = auto()
    ENTERING_TRAVELERS = auto()
    VALIDATING_TRAVELERS = auto()
    CREATING_RESERVATION = auto()
    DISPLAYING_CONFIRMATION = auto()
    HANDLING_ERROR = auto()


@dataclass
class BookingContext:
    """
    Context object that travels through the state machine.
    Holds all data needed for booking process.
    """
    # Search criteria
    departure_city: Optional[str] = None
    arrival_city: Optional[str] = None
    max_stops: int = 2
    
    # Search results
    connections: List = None
    
    # Selected connection
    selected_connection = None
    
    # Travelers
    travelers: List[Tuple[str, str, str, int]] = None
    
    # Validation results
    validation_errors: List[str] = None
    
    # Created trip
    trip_id: Optional[int] = None
    ticket_ids: List[int] = None
    
    # Error handling
    last_error: Optional[str] = None
    
    # State tracking
    current_state: BookingState = BookingState.IDLE
    previous_state: Optional[BookingState] = None
    
    def __post_init__(self):
        if self.connections is None:
            self.connections = []
        if self.travelers is None:
            self.travelers = []
        if self.validation_errors is None:
            self.validation_errors = []
        if self.ticket_ids is None:
            self.ticket_ids = []


class BookingStateMachine:
    """
    State machine for booking process.
    
    Implements the UML state machine diagram from diagrams/state-machine-booking.puml
    
    States:
    1. IDLE - No active booking
    2. SEARCHING_CONNECTION - Client entering search criteria
    3. DISPLAYING_RESULTS - Showing available connections
    4. SELECTING_CONNECTION - Client selecting a connection
    5. ENTERING_TRAVELERS - Collecting traveler information
    6. VALIDATING_TRAVELERS - Checking business rules
    7. CREATING_RESERVATION - Database transaction
    8. DISPLAYING_CONFIRMATION - Success message
    9. HANDLING_ERROR - Error recovery
    """
    
    def __init__(self, rail_network, booking_system):
        """
        Initialize state machine with dependencies.
        
        Args:
            rail_network: RailNetwork instance for search
            booking_system: BookingSystem instance for reservations
        """
        self.rail_network = rail_network
        self.booking_system = booking_system
        self.context = BookingContext()
        
        # State handlers map
        self.state_handlers = {
            BookingState.IDLE: self._handle_idle,
            BookingState.SEARCHING_CONNECTION: self._handle_searching,
            BookingState.DISPLAYING_RESULTS: self._handle_displaying_results,
            BookingState.SELECTING_CONNECTION: self._handle_selecting,
            BookingState.ENTERING_TRAVELERS: self._handle_entering_travelers,
            BookingState.VALIDATING_TRAVELERS: self._handle_validating,
            BookingState.CREATING_RESERVATION: self._handle_creating,
            BookingState.DISPLAYING_CONFIRMATION: self._handle_confirmation,
            BookingState.HANDLING_ERROR: self._handle_error
        }
    
    def transition_to(self, new_state: BookingState, reason: str = ""):
        """
        Transition to a new state.
        
        Args:
            new_state: Target state
            reason: Reason for transition (for logging)
        """
        print(f"STATE TRANSITION: {self.context.current_state.name} -> {new_state.name} ({reason})")
        self.context.previous_state = self.context.current_state
        self.context.current_state = new_state
    
    # ============ State Handlers ============
    
    def _handle_idle(self):
        """
        IDLE state: System ready, no active booking.
        
        Transitions:
        - To SEARCHING_CONNECTION: Client initiates booking
        """
        print("\n=== IDLE STATE ===")
        print("System ready for new booking")
        return "awaiting_initiation"
    
    def _handle_searching(self):
        """
        SEARCHING_CONNECTION state: Client entering search criteria.
        
        Transitions:
        - To DISPLAYING_RESULTS: Valid criteria, search executed
        - To SEARCHING_CONNECTION: Invalid criteria, retry
        - To IDLE: Cancel
        """
        print("\n=== SEARCHING CONNECTION ===")
        
        # Validate criteria
        if not self.context.departure_city or not self.context.arrival_city:
            self.context.validation_errors.append("Departure and arrival cities required")
            return "invalid_criteria"
        
        # Execute search
        try:
            self.context.connections = self.rail_network.search(
                departure_city=self.context.departure_city,
                arrival_city=self.context.arrival_city,
                max_stops=self.context.max_stops,
                layover_policy="strict"
            )
            
            if not self.context.connections:
                self.context.validation_errors.append("No connections found")
                return "no_results"
            
            self.transition_to(BookingState.DISPLAYING_RESULTS, "search successful")
            return "search_complete"
            
        except Exception as e:
            self.context.last_error = str(e)
            self.transition_to(BookingState.HANDLING_ERROR, "search failed")
            return "error"
    
    def _handle_displaying_results(self):
        """
        DISPLAYING_RESULTS state: Showing available connections.
        
        Transitions:
        - To SELECTING_CONNECTION: Client selects connection
        - To SEARCHING_CONNECTION: Refine search
        - To IDLE: Cancel
        """
        print("\n=== DISPLAYING RESULTS ===")
        print(f"Found {len(self.context.connections)} connections")
        
        for i, conn in enumerate(self.context.connections):
            print(f"{i+1}. {conn.origin} -> {conn.destination} "
                  f"({conn.total_travel_minutes} min, {len(conn.legs)-1} stops)")
        
        return "awaiting_selection"
    
    def _handle_selecting(self):
        """
        SELECTING_CONNECTION state: Connection selected.
        
        Transitions:
        - To ENTERING_TRAVELERS: Confirm selection
        - To DISPLAYING_RESULTS: Change selection
        - To IDLE: Cancel
        """
        print("\n=== SELECTING CONNECTION ===")
        
        if self.context.selected_connection is None:
            return "no_selection"
        
        print(f"Selected: {self.context.selected_connection.origin} -> "
              f"{self.context.selected_connection.destination}")
        
        self.transition_to(BookingState.ENTERING_TRAVELERS, "connection confirmed")
        return "confirmed"
    
    def _handle_entering_travelers(self):
        """
        ENTERING_TRAVELERS state: Collecting traveler information.
        
        Transitions:
        - To VALIDATING_TRAVELERS: All travelers entered
        - To SELECTING_CONNECTION: Back to connection
        - To IDLE: Cancel
        """
        print("\n=== ENTERING TRAVELERS ===")
        
        if not self.context.travelers:
            return "awaiting_travelers"
        
        print(f"Travelers entered: {len(self.context.travelers)}")
        for i, (first, last, id_num, age) in enumerate(self.context.travelers):
            print(f"  {i+1}. {first} {last} (ID: {id_num}, Age: {age})")
        
        self.transition_to(BookingState.VALIDATING_TRAVELERS, "travelers entered")
        return "ready_to_validate"
    
    def _handle_validating(self):
        """
        VALIDATING_TRAVELERS state: Checking business rules.
        
        OCL Pre-conditions checked here:
        - travelers->notEmpty()
        - No duplicate travelers
        - No existing bookings
        - All ages >= 0
        
        Transitions:
        - To CREATING_RESERVATION: Validation success
        - To ENTERING_TRAVELERS: Validation failed, allow correction
        """
        print("\n=== VALIDATING TRAVELERS ===")
        self.context.validation_errors = []
        
        # Check 1: Format validation
        for first, last, id_num, age in self.context.travelers:
            if not first or not last:
                self.context.validation_errors.append("Names cannot be empty")
            if not id_num:
                self.context.validation_errors.append("ID number required")
            if age < 0:
                self.context.validation_errors.append(f"Invalid age: {age}")
        
        # Check 2: Duplicate travelers
        seen = set()
        for first, last, id_num, age in self.context.travelers:
            key = (last.lower(), id_num)
            if key in seen:
                self.context.validation_errors.append(
                    f"Duplicate traveler: {first} {last}"
                )
            seen.add(key)
        
        # Check 3: Existing bookings
        from booking_system_v3 import Client
        for first, last, id_num, age in self.context.travelers:
            client = Client(first, last, id_num, age)
            if self.booking_system._has_booking_for_connection(
                client, self.context.selected_connection
            ):
                self.context.validation_errors.append(
                    f"Client {first} {last} already has reservation for this connection"
                )
        
        if self.context.validation_errors:
            print("VALIDATION FAILED:")
            for error in self.context.validation_errors:
                print(f"  - {error}")
            self.transition_to(BookingState.ENTERING_TRAVELERS, "validation failed")
            return "validation_failed"
        
        print("VALIDATION PASSED")
        self.transition_to(BookingState.CREATING_RESERVATION, "validation success")
        return "validation_success"
    
    def _handle_creating(self):
        """
        CREATING_RESERVATION state: Database transaction.
        
        Sub-states:
        1. Generating trip ID
        2. Inserting trip legs
        3. Creating clients
        4. Generating tickets
        5. Committing transaction
        
        OCL Post-conditions ensured:
        - trip_id > 0
        - Reservations created
        - Unique ticket IDs
        
        Transitions:
        - To DISPLAYING_CONFIRMATION: Success
        - To HANDLING_ERROR: Failed (rollback)
        """
        print("\n=== CREATING RESERVATION ===")
        print("Starting database transaction...")
        
        try:
            # Execute booking
            trip = self.booking_system.book_trip(
                self.context.selected_connection,
                self.context.travelers
            )
            
            # Store results
            self.context.trip_id = trip.trip_id
            self.context.ticket_ids = [res.ticket.ticket_id for res in trip.reservations]
            
            print(f"SUCCESS: Trip {self.context.trip_id} created")
            print(f"Tickets: {self.context.ticket_ids}")
            
            # Verify post-conditions
            assert trip.trip_id > 0, "Post-condition failed: trip_id must be positive"
            assert len(trip.reservations) == len(self.context.travelers), \
                "Post-condition failed: reservation count mismatch"
            
            self.transition_to(BookingState.DISPLAYING_CONFIRMATION, "reservation created")
            return "success"
            
        except Exception as e:
            self.context.last_error = str(e)
            print(f"ERROR: {e}")
            self.transition_to(BookingState.HANDLING_ERROR, "reservation failed")
            return "error"
    
    def _handle_confirmation(self):
        """
        DISPLAYING_CONFIRMATION state: Success message.
        
        Transitions:
        - To IDLE: Acknowledged
        """
        print("\n=== BOOKING CONFIRMED ===")
        print(f"Trip ID: {self.context.trip_id}")
        print(f"Travelers: {len(self.context.travelers)}")
        print(f"Tickets: {', '.join(map(str, self.context.ticket_ids))}")
        
        connection = self.context.selected_connection
        total_price = connection.price("second") * len(self.context.travelers)
        print(f"Total Cost: {total_price:.2f} EUR")
        
        self.transition_to(BookingState.IDLE, "booking complete")
        return "complete"
    
    def _handle_error(self):
        """
        HANDLING_ERROR state: Error recovery.
        
        Transitions:
        - To ENTERING_TRAVELERS: Retry
        - To IDLE: Give up
        """
        print("\n=== ERROR HANDLING ===")
        print(f"Error: {self.context.last_error}")
        
        if self.context.validation_errors:
            print("Validation errors:")
            for error in self.context.validation_errors:
                print(f"  - {error}")
        
        return "awaiting_recovery_decision"
    
    # ============ Public API ============
    
    def start_booking(self, departure: str, arrival: str, max_stops: int = 2):
        """Initiate booking process."""
        self.context = BookingContext()
        self.context.departure_city = departure
        self.context.arrival_city = arrival
        self.context.max_stops = max_stops
        
        self.transition_to(BookingState.SEARCHING_CONNECTION, "booking initiated")
        return self._handle_searching()
    
    def select_connection(self, connection_index: int):
        """Select a connection from search results."""
        if 0 <= connection_index < len(self.context.connections):
            self.context.selected_connection = self.context.connections[connection_index]
            self.transition_to(BookingState.SELECTING_CONNECTION, "connection selected")
            return self._handle_selecting()
        return "invalid_index"
    
    def add_travelers(self, travelers: List[Tuple[str, str, str, int]]):
        """Add traveler information."""
        self.context.travelers = travelers
        return self._handle_entering_travelers()
    
    def execute_current_state(self):
        """Execute current state handler."""
        handler = self.state_handlers.get(self.context.current_state)
        if handler:
            return handler()
        return "unknown_state"
    
    def cancel(self):
        """Cancel booking and return to IDLE."""
        print("\nBooking cancelled")
        self.transition_to(BookingState.IDLE, "cancelled by user")
        return self._handle_idle()
    
    def get_current_state(self) -> BookingState:
        """Get current state."""
        return self.context.current_state
    
    def is_complete(self) -> bool:
        """Check if booking is complete."""
        return (self.context.current_state == BookingState.IDLE and 
                self.context.trip_id is not None)

