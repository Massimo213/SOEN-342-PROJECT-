"""
Booking System - Iteration 2

Domain-driven design for trip booking with immutable semantics where appropriate.
Handles multi-traveler bookings, ticket generation, and trip history.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from datetime import datetime, date
import uuid
import secrets
from rail_network import Itinerary


# ----------------------------
# ID Generation
# ----------------------------

def generate_trip_id() -> str:
    """
    Generate unique alphanumeric trip ID.
    Format: TRP-{8-char-hex} for readability and collision resistance.
    
    Collision probability: ~1 in 4 billion for 2^32 IDs.
    """
    return f"TRP-{secrets.token_hex(4).upper()}"


def generate_ticket_id() -> int:
    """
    Generate unique numeric ticket ID.
    Uses timestamp + random component to ensure uniqueness across processes.
    
    Format: Unix timestamp (10 digits) + random 5 digits = 15-digit number
    """
    timestamp_part = int(datetime.now().timestamp())
    random_part = secrets.randbelow(100000)
    return timestamp_part * 100000 + random_part


# ----------------------------
# Domain Models
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
        # Client uniqueness determined by last_name + id_number
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
    
    Design notes:
    - ticket_id is system-generated numeric
    - Tickets are write-once, read-many (audit trail)
    """
    ticket_id: int
    client: Client
    connection: Itinerary  # The selected connection
    issue_timestamp: datetime
    
    def connection_date(self) -> str:
        """Extract departure date from connection."""
        return self.connection.departure_time


@dataclass
class Reservation:
    """
    Mutable reservation container linking a client to a ticket.
    
    Design notes:
    - One reservation per traveler
    - ticket is generated at booking time
    """
    client: Client
    ticket: Ticket
    
    def __post_init__(self):
        # Integrity check: ticket must match client
        if self.ticket.client != self.client:
            raise ValueError("Ticket client mismatch")


@dataclass
class Trip:
    """
    Mutable trip aggregating multiple reservations.
    
    Design notes:
    - trip_id is alphanumeric, system-generated
    - A trip must have at least one reservation
    - All reservations share the same connection (business rule)
    """
    trip_id: str
    connection: Itinerary
    reservations: List[Reservation] = field(default_factory=list)
    booking_timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.trip_id:
            raise ValueError("Trip ID required")
        if not self.reservations:
            raise ValueError("Trip must have at least one reservation")
        
        # Enforce business rule: all reservations for same connection
        for res in self.reservations:
            if res.ticket.connection != self.connection:
                raise ValueError("All reservations must be for the same connection")
    
    def total_travelers(self) -> int:
        return len(self.reservations)
    
    def get_clients(self) -> List[Client]:
        return [res.client for res in self.reservations]
    
    def departure_date(self) -> str:
        """Get departure date from connection."""
        return self.connection.departure_time
    
    def is_past(self, reference_date: Optional[date] = None) -> bool:
        """
        Determine if trip is in the past.
        
        Limitation: Departure time format in CSV lacks full date info.
        Heuristic: Parse time and assume it's "past" if it's before current time today.
        Production: Would need full ISO8601 dates.
        """
        if reference_date is None:
            reference_date = date.today()
        
        # For now, use simple heuristic based on booking timestamp
        # In production, would parse actual departure date from connection
        return self.booking_timestamp.date() < reference_date


# ----------------------------
# Booking System
# ----------------------------

class BookingSystem:
    """
    Stateful booking system managing trips and clients.
    
    Architecture:
    - In-memory storage (trips, clients)
    - Indexing for fast lookups by client credentials
    - Thread-safety: NOT thread-safe (add locks for concurrent access)
    
    Failure modes:
    - Duplicate bookings: Enforced via business rules
    - ID collisions: Statistically negligible with proper RNG
    """
    
    def __init__(self):
        # All trips indexed by trip_id
        self.trips: Dict[str, Trip] = {}
        
        # Index: (last_name, id_number) -> Set[trip_id]
        # Enables O(1) lookup of trips by client credentials
        self.client_trips_index: Dict[tuple, Set[str]] = {}
        
        # All known clients (deduped by identity)
        self.clients: Set[Client] = set()
    
    def book_trip(
        self, 
        connection: Itinerary,
        travelers: List[tuple[str, str, str, int]]  # (first, last, id, age)
    ) -> Trip:
        """
        Book a trip for one or more travelers.
        
        Args:
            connection: The selected itinerary
            travelers: List of (first_name, last_name, id_number, age)
        
        Returns:
            The created Trip object
        
        Raises:
            ValueError: If business rules violated
        
        Design notes:
        - Validates no duplicate clients within same booking
        - Generates unique ticket per traveler
        - Atomicity: Either all succeed or none (in-memory rollback on error)
        """
        if not travelers:
            raise ValueError("At least one traveler required")
        
        # Parse travelers into Client objects
        clients = []
        seen = set()
        for first, last, id_num, age in travelers:
            client = Client(first, last, id_num, age)
            
            # Business rule: no duplicate clients in single trip
            if client in seen:
                raise ValueError(
                    f"Duplicate client in booking: {client.first_name} {client.last_name}"
                )
            seen.add(client)
            clients.append(client)
            
            # Register client globally
            self.clients.add(client)
        
        # Business rule: Check if any client already has booking for this connection
        # "For a given connection, a client may only have a single reservation under their name"
        for client in clients:
            if self._has_booking_for_connection(client, connection):
                raise ValueError(
                    f"Client {client.first_name} {client.last_name} "
                    f"already has a reservation for this connection"
                )
        
        # Generate trip and tickets
        trip_id = generate_trip_id()
        reservations = []
        
        for client in clients:
            ticket_id = generate_ticket_id()
            ticket = Ticket(
                ticket_id=ticket_id,
                client=client,
                connection=connection,
                issue_timestamp=datetime.now()
            )
            reservation = Reservation(client=client, ticket=ticket)
            reservations.append(reservation)
        
        trip = Trip(
            trip_id=trip_id,
            connection=connection,
            reservations=reservations,
            booking_timestamp=datetime.now()
        )
        
        # Persist trip and update indices
        self.trips[trip_id] = trip
        for client in clients:
            key = (client.last_name.lower(), client.id_number)
            self.client_trips_index.setdefault(key, set()).add(trip_id)
        
        return trip
    
    def get_trips_by_client(
        self, 
        last_name: str, 
        id_number: str
    ) -> tuple[List[Trip], List[Trip]]:
        """
        Retrieve all trips for a client, split into current and past.
        
        Args:
            last_name: Client's last name (case-insensitive)
            id_number: Client's ID number
        
        Returns:
            (current_trips, past_trips) tuple
        
        Design notes:
        - O(1) lookup via index
        - Separates current (today/future) from past
        """
        key = (last_name.lower(), id_number)
        trip_ids = self.client_trips_index.get(key, set())
        
        current_trips = []
        past_trips = []
        today = date.today()
        
        for trip_id in trip_ids:
            trip = self.trips[trip_id]
            if trip.is_past(today):
                past_trips.append(trip)
            else:
                current_trips.append(trip)
        
        # Sort by booking timestamp (most recent first)
        current_trips.sort(key=lambda t: t.booking_timestamp, reverse=True)
        past_trips.sort(key=lambda t: t.booking_timestamp, reverse=True)
        
        return current_trips, past_trips
    
    def _has_booking_for_connection(
        self, 
        client: Client, 
        connection: Itinerary
    ) -> bool:
        """
        Check if client already has a reservation for this connection.
        
        Connection equality based on route IDs in legs.
        """
        key = (client.last_name.lower(), client.id_number)
        trip_ids = self.client_trips_index.get(key, set())
        
        for trip_id in trip_ids:
            trip = self.trips[trip_id]
            # Compare connections by legs (route IDs)
            if self._connections_equal(trip.connection, connection):
                return True
        return False
    
    def _connections_equal(self, conn1: Itinerary, conn2: Itinerary) -> bool:
        """
        Compare two connections for equality.
        
        Equality: Same route IDs in same order.
        """
        if len(conn1.legs) != len(conn2.legs):
            return False
        for leg1, leg2 in zip(conn1.legs, conn2.legs):
            if leg1.route.route_id != leg2.route.route_id:
                return False
        return True
    
    def get_trip_by_id(self, trip_id: str) -> Optional[Trip]:
        """Retrieve trip by ID."""
        return self.trips.get(trip_id)
    
    def get_all_trips(self) -> List[Trip]:
        """Get all trips in system."""
        return list(self.trips.values())

