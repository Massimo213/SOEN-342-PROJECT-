"""
Booking System - Iteration 3 (Database-backed)

CHANGES FROM ITERATION 2:
- Trip IDs: alphanumeric (TRP-XXXX) → numeric (INTEGER auto-increment)
- Storage: in-memory dicts → SQLite database
- Persistence: session-based → durable across restarts
- Client deduplication: hash-based sets → DB UNIQUE constraint

Domain-driven design preserved with database persistence layer.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
from datetime import datetime, date
from rail_network import Itinerary, TrainRoute, Leg
from database import Database


# ----------------------------
# Domain Models (Kept for compatibility)
# ----------------------------

@dataclass(frozen=True)
class Client:
    """
    Immutable client identity.
    
    Design notes:
    - frozen=True ensures clients can be used as dict keys/set members
    - id_number is generic (passport/state-id)
    - Hash based on (last_name, id_number) for deduplication
    """
    first_name: str
    last_name: str
    id_number: str
    age: int
    
    def __post_init__(self):
        if self.age < 0:
            raise ValueError(f"Invalid age: {self.age}")
        if not self.first_name or not self.last_name:
            raise ValueError("Names cannot be empty")
        if not self.id_number:
            raise ValueError("ID number cannot be empty")
    
    def __hash__(self) -> int:
        return hash((self.last_name.lower(), self.id_number))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Client):
            return False
        return (self.last_name.lower() == other.last_name.lower() and 
                self.id_number == other.id_number)


@dataclass(frozen=True)
class Ticket:
    """
    Immutable ticket documenting a single reservation.
    
    **Iteration 3 Change:** ticket_id now comes from database auto-increment
    """
    ticket_id: int
    client: Client
    connection: Itinerary
    issue_timestamp: datetime
    
    def connection_date(self) -> str:
        """Extract departure date from connection."""
        return self.connection.departure_time


@dataclass
class Reservation:
    """
    Mutable reservation container linking a client to a ticket.
    """
    client: Client
    ticket: Ticket
    
    def __post_init__(self):
        if self.ticket.client != self.client:
            raise ValueError("Ticket client mismatch")


@dataclass
class Trip:
    """
    Mutable trip aggregating multiple reservations.
    
    **Iteration 3 Change:** trip_id is now numeric (INTEGER)
    """
    trip_id: int  # Changed from str to int
    connection: Itinerary
    reservations: List[Reservation]
    booking_timestamp: datetime
    
    def __post_init__(self):
        if not isinstance(self.trip_id, int):
            raise ValueError(f"Trip ID must be integer, got {type(self.trip_id)}")
        if not self.reservations:
            raise ValueError("Trip must have at least one reservation")
        
        for res in self.reservations:
            if res.ticket.connection != self.connection:
                raise ValueError("All reservations must be for the same connection")
    
    def total_travelers(self) -> int:
        return len(self.reservations)
    
    def get_clients(self) -> List[Client]:
        return [res.client for res in self.reservations]
    
    def departure_date(self) -> str:
        return self.connection.departure_time
    
    def is_past(self, reference_date: Optional[date] = None) -> bool:
        """
        Determine if trip is in the past.
        """
        if reference_date is None:
            reference_date = date.today()
        return self.booking_timestamp.date() < reference_date


# ----------------------------
# Booking System (Database-backed)
# ----------------------------

class BookingSystem:
    """
    Database-backed booking system managing trips and clients.
    
    **Iteration 3 Architecture:**
    - Persistence: SQLite database (via Database class)
    - Trip IDs: Numeric auto-increment (was alphanumeric)
    - Ticket IDs: Numeric auto-increment
    - Client deduplication: DB UNIQUE constraint on (last_name, id_number)
    - Transactions: Atomic booking operations
    
    Failure modes:
    - Database errors: Rollback via context manager
    - Duplicate bookings: Enforced via application logic
    - ID collisions: Impossible (DB auto-increment)
    """
    
    def __init__(self, db: Database):
        """
        Initialize booking system with database connection.
        
        Args:
            db: Database instance (can be in-memory for testing)
        """
        self.db = db
    
    def book_trip(
        self, 
        connection: Itinerary,
        travelers: List[Tuple[str, str, str, int]]  # (first, last, id, age)
    ) -> Trip:
        """
        Book a trip for one or more travelers.
        
        **Iteration 3 Changes:**
        - Returns Trip with numeric trip_id
        - Persists to database
        - Transaction atomic (all-or-nothing)
        
        Args:
            connection: The selected itinerary
            travelers: List of (first_name, last_name, id_number, age)
        
        Returns:
            The created Trip object with numeric ID
        
        Raises:
            ValueError: If business rules violated
            sqlite3.Error: If database operation fails
        """
        if not travelers:
            raise ValueError("At least one traveler required")
        
        # Parse travelers into Client objects
        clients = []
        seen = set()
        for first, last, id_num, age in travelers:
            client = Client(first, last, id_num, age)
            
            if client in seen:
                raise ValueError(
                    f"Duplicate client in booking: {client.first_name} {client.last_name}"
                )
            seen.add(client)
            clients.append(client)
        
        # Check for duplicate bookings
        for client in clients:
            if self._has_booking_for_connection(client, connection):
                raise ValueError(
                    f"Client {client.first_name} {client.last_name} "
                    f"already has a reservation for this connection"
                )
        
        # Database transaction: Create trip
        trip_id = self.db.create_trip(
            departure_city=connection.origin,
            arrival_city=connection.destination,
            departure_time=connection.departure_time,
            arrival_time=connection.arrival_time
        )
        
        # Store trip legs
        for i, leg in enumerate(connection.legs):
            self.db.add_trip_leg(trip_id, leg.route.route_id, i)
        
        # Create reservations
        reservations = []
        for client in clients:
            # Get or create client in database
            client_id = self.db.get_or_create_client(
                client.first_name,
                client.last_name,
                client.id_number,
                client.age
            )
            
            # Create ticket
            ticket_id = self.db.create_ticket(client_id, trip_id)
            
            # Build domain objects
            ticket = Ticket(
                ticket_id=ticket_id,
                client=client,
                connection=connection,
                issue_timestamp=datetime.now()
            )
            reservation = Reservation(client=client, ticket=ticket)
            reservations.append(reservation)
        
        # Build trip object
        trip = Trip(
            trip_id=trip_id,
            connection=connection,
            reservations=reservations,
            booking_timestamp=datetime.now()
        )
        
        return trip
    
    def get_trips_by_client(
        self, 
        last_name: str, 
        id_number: str
    ) -> Tuple[List[Trip], List[Trip]]:
        """
        Retrieve all trips for a client, split into current and past.
        
        Args:
            last_name: Client's last name (case-insensitive)
            id_number: Client's ID number
        
        Returns:
            (current_trips, past_trips) tuple
        """
        # Find client
        client_id = self.db.get_client_by_credentials(last_name, id_number)
        if client_id is None:
            return ([], [])
        
        # Get all trips for client
        trip_dicts = self.db.get_trips_for_client(client_id)
        
        # Reconstruct Trip objects
        trips = []
        for trip_dict in trip_dicts:
            trip_obj = self._reconstruct_trip(trip_dict['trip_id'])
            if trip_obj:
                trips.append(trip_obj)
        
        # Separate current and past
        current_trips = []
        past_trips = []
        today = date.today()
        
        for trip in trips:
            if trip.is_past(today):
                past_trips.append(trip)
            else:
                current_trips.append(trip)
        
        # Sort by booking timestamp
        current_trips.sort(key=lambda t: t.booking_timestamp, reverse=True)
        past_trips.sort(key=lambda t: t.booking_timestamp, reverse=True)
        
        return current_trips, past_trips
    
    def get_trip_by_id(self, trip_id: int) -> Optional[Trip]:
        """Retrieve trip by numeric ID."""
        return self._reconstruct_trip(trip_id)
    
    def get_all_trips(self) -> List[Trip]:
        """Get all trips in system."""
        # Not efficient for large datasets; use for testing only
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT trip_id FROM trips")
            trip_ids = [row['trip_id'] for row in cursor.fetchall()]
        
        trips = []
        for trip_id in trip_ids:
            trip = self._reconstruct_trip(trip_id)
            if trip:
                trips.append(trip)
        return trips
    
    # ============ Private Helper Methods ============
    
    def _reconstruct_trip(self, trip_id: int) -> Optional[Trip]:
        """
        Reconstruct Trip domain object from database.
        
        Args:
            trip_id: Numeric trip identifier
        
        Returns:
            Trip object or None if not found
        """
        trip_dict = self.db.get_trip_by_id(trip_id)
        if not trip_dict:
            return None
        
        # Reconstruct connection (Itinerary)
        route_dicts = self.db.get_trip_legs(trip_id)
        if not route_dicts:
            return None
        
        legs = []
        for route_dict in route_dicts:
            route = TrainRoute(
                route_id=route_dict['route_id'],
                departure_city=route_dict['departure_city'],
                arrival_city=route_dict['arrival_city'],
                departure_time=route_dict['departure_time'],
                arrival_time=route_dict['arrival_time'],
                train_type=route_dict['train_type'],
                days_of_operation=route_dict['days_of_operation'],
                first_class_rate=route_dict['first_class_rate'],
                second_class_rate=route_dict['second_class_rate']
            )
            legs.append(Leg(route))
        
        connection = Itinerary(legs)
        
        # Reconstruct reservations
        ticket_dicts = self.db.get_tickets_for_trip(trip_id)
        reservations = []
        
        for ticket_dict in ticket_dicts:
            client = Client(
                first_name=ticket_dict['first_name'],
                last_name=ticket_dict['last_name'],
                id_number=ticket_dict['id_number'],
                age=ticket_dict['age']
            )
            
            ticket = Ticket(
                ticket_id=ticket_dict['ticket_id'],
                client=client,
                connection=connection,
                issue_timestamp=datetime.fromisoformat(ticket_dict['issue_timestamp'])
            )
            
            reservation = Reservation(client=client, ticket=ticket)
            reservations.append(reservation)
        
        # Build Trip object
        trip = Trip(
            trip_id=trip_id,
            connection=connection,
            reservations=reservations,
            booking_timestamp=datetime.fromisoformat(trip_dict['booking_timestamp'])
        )
        
        return trip
    
    def _has_booking_for_connection(
        self, 
        client: Client, 
        connection: Itinerary
    ) -> bool:
        """
        Check if client already has a reservation for this connection.
        
        Connection equality based on route IDs in legs.
        """
        client_id = self.db.get_client_by_credentials(client.last_name, client.id_number)
        if client_id is None:
            return False
        
        trip_dicts = self.db.get_trips_for_client(client_id)
        
        for trip_dict in trip_dicts:
            trip_legs = self.db.get_trip_legs(trip_dict['trip_id'])
            trip_route_ids = [leg['route_id'] for leg in trip_legs]
            connection_route_ids = [leg.route.route_id for leg in connection.legs]
            
            if trip_route_ids == connection_route_ids:
                return True
        
        return False

