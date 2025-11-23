# OCL Constraints Specification
**SOEN 342 - Final Iteration**  
**Version:** 1.0  
**Date:** November 23, 2025

---

## 1. Introduction

This document specifies Object Constraint Language (OCL) expressions for the Rail Network Booking System. These constraints enforce business rules at the model level and are implemented as runtime validations.

---

## 2. OCL Expression for Reservation Creation Method

### Context: BookingSystem::book_trip()

```ocl
context BookingSystem::book_trip(connection: Itinerary, travelers: List<Tuple>): Trip

pre: -- Preconditions (must be true before method execution)
    -- At least one traveler required
    travelers->notEmpty() and
    
    -- Connection must be valid
    connection <> null and
    connection.legs->notEmpty() and
    
    -- All traveler tuples must have 4 elements (first_name, last_name, id_number, age)
    travelers->forAll(t | t.size() = 4) and
    
    -- All ages must be non-negative
    travelers->forAll(t | t->at(4) >= 0) and
    
    -- No duplicate travelers in same booking (by last_name + id_number)
    travelers->forAll(t1, t2 | 
        t1 <> t2 implies (t1->at(2) <> t2->at(2) or t1->at(3) <> t2->at(3))) and
    
    -- No traveler already has reservation for this connection
    travelers->forAll(t | 
        not self.hasBookingForConnection(
            Client.new(t->at(1), t->at(2), t->at(3), t->at(4)), 
            connection
        )
    )

post: -- Postconditions (must be true after method execution)
    -- Trip created and returned
    result <> null and
    
    -- Trip has numeric ID > 0
    result.trip_id > 0 and
    
    -- Trip has correct number of reservations
    result.reservations->size() = travelers->size() and
    
    -- Each reservation has unique ticket
    result.reservations->forAll(r1, r2 | 
        r1 <> r2 implies r1.ticket.ticket_id <> r2.ticket.ticket_id) and
    
    -- All reservations reference same connection
    result.reservations->forAll(r | 
        r.ticket.connection = connection) and
    
    -- Trip added to system
    self.trips->includes(result.trip_id) and
    
    -- All clients registered in system
    travelers->forAll(t | 
        self.clients->exists(c | 
            c.last_name = t->at(2) and c.id_number = t->at(3)))

-- Invariant (must always be true during execution)
inv validState:
    -- Database connection is open
    self.db <> null
```

---

## 3. OCL Expressions for Reservation Class

### Context: Reservation

```ocl
context Reservation

-- Class Invariants (must always be true for any Reservation instance)

inv clientTicketMatch:
    -- Ticket must be issued to the client in this reservation
    self.ticket.client = self.client
    
inv nonNullClient:
    -- Client cannot be null
    self.client <> null
    
inv nonNullTicket:
    -- Ticket cannot be null
    self.ticket <> null
    
inv validClientIdentity:
    -- Client must have valid identity
    self.client.last_name <> null and
    self.client.last_name <> '' and
    self.client.id_number <> null and
    self.client.id_number <> '' and
    self.client.age >= 0
    
inv ticketIssued:
    -- Ticket must have positive ID (has been issued)
    self.ticket.ticket_id > 0
    
inv ticketTimestamp:
    -- Ticket must have issue timestamp
    self.ticket.issue_timestamp <> null and
    self.ticket.issue_timestamp <= Date.now()
    
inv connectionValid:
    -- Ticket must reference a valid connection
    self.ticket.connection <> null and
    self.ticket.connection.legs->notEmpty()
```

### Context: Reservation Constructor

```ocl
context Reservation::new(client: Client, ticket: Ticket): Reservation

pre: -- Preconditions for creating a reservation
    -- Client must be valid
    client <> null and
    client.last_name <> '' and
    client.id_number <> '' and
    client.age >= 0 and
    
    -- Ticket must be valid
    ticket <> null and
    ticket.ticket_id > 0 and
    ticket.client = client and
    
    -- Ticket and client must match
    ticket.client.last_name = client.last_name and
    ticket.client.id_number = client.id_number

post: -- Postconditions after creating a reservation
    -- Reservation created with correct attributes
    result.client = client and
    result.ticket = ticket and
    
    -- All invariants satisfied
    result.clientTicketMatch and
    result.nonNullClient and
    result.nonNullTicket
```

---

## 4. Additional OCL Constraints for Related Classes

### Context: Trip

```ocl
context Trip

inv hasReservations:
    -- Trip must have at least one reservation
    self.reservations->notEmpty()
    
inv numericTripId:
    -- Trip ID must be positive integer
    self.trip_id > 0
    
inv sameConnection:
    -- All reservations must be for the same connection
    self.reservations->forAll(r | 
        r.ticket.connection = self.connection)
    
inv validBookingTime:
    -- Booking timestamp must be in the past
    self.booking_timestamp <= Date.now()
    
inv uniqueTickets:
    -- All tickets in trip must be unique
    self.reservations->forAll(r1, r2 | 
        r1 <> r2 implies r1.ticket.ticket_id <> r2.ticket.ticket_id)

derive total_travelers: Integer =
    -- Derived attribute: number of travelers
    self.reservations->size()
```

### Context: Client

```ocl
context Client

inv nonEmptyName:
    -- Names cannot be empty
    self.first_name <> null and self.first_name <> '' and
    self.last_name <> null and self.last_name <> ''
    
inv nonEmptyId:
    -- ID number cannot be empty
    self.id_number <> null and self.id_number <> ''
    
inv validAge:
    -- Age must be non-negative and realistic
    self.age >= 0 and self.age <= 150
    
inv immutable:
    -- Client is immutable (frozen dataclass)
    -- Once created, attributes cannot change
    self@pre.first_name = self.first_name and
    self@pre.last_name = self.last_name and
    self@pre.id_number = self.id_number and
    self@pre.age = self.age
```

### Context: Ticket

```ocl
context Ticket

inv positiveId:
    -- Ticket ID must be positive
    self.ticket_id > 0
    
inv hasClient:
    -- Ticket must be issued to a client
    self.client <> null
    
inv hasConnection:
    -- Ticket must be for a connection
    self.connection <> null
    
inv hasTimestamp:
    -- Ticket must have issue timestamp
    self.issue_timestamp <> null and
    self.issue_timestamp <= Date.now()
    
inv immutable:
    -- Tickets are immutable (audit trail)
    self@pre.ticket_id = self.ticket_id and
    self@pre.client = self.client and
    self@pre.connection = self.connection and
    self@pre.issue_timestamp = self.issue_timestamp
```

---

## 5. Business Rule Constraints

### No Duplicate Bookings

```ocl
context BookingSystem

inv noDuplicateBookings:
    -- A client can only have one reservation per connection
    self.trips->forAll(t1, t2 | 
        t1 <> t2 implies
            not (t1.reservations->exists(r1 | 
                 t2.reservations->exists(r2 | 
                     r1.client = r2.client and
                     self.connectionsEqual(t1.connection, t2.connection)
                 )
            )
        )
    )
```

### Layover Policy Compliance

```ocl
context Itinerary

inv validLayovers:
    -- All layovers must comply with time-based policy
    self.legs->size() > 1 implies
        Sequence{1..self.legs->size()-1}->forAll(i |
            let prevArrival = self.legs->at(i).route.arr_min in
            let nextDeparture = self.legs->at(i+1).route.dep_min in
            let gap = if nextDeparture >= prevArrival 
                     then nextDeparture - prevArrival
                     else (1440 - prevArrival) + nextDeparture in
            let isDaytime = (prevArrival >= 360 and prevArrival < 1320) in
            
            -- Apply policy based on time of day
            if isDaytime
            then gap >= 15 and gap <= 120
            else gap >= 15 and gap <= 30
            endif
        )
```

---

## 6. Database Constraints

### Foreign Key Integrity

```ocl
context Database

inv clientForeignKeys:
    -- All tickets reference existing clients
    self.tickets->forAll(t | 
        self.clients->exists(c | c.client_id = t.client_id))
    
inv tripForeignKeys:
    -- All tickets reference existing trips
    self.tickets->forAll(t | 
        self.trips->exists(trip | trip.trip_id = t.trip_id))
    
inv tripLegForeignKeys:
    -- All trip legs reference existing trips and routes
    self.trip_legs->forAll(tl | 
        self.trips->exists(t | t.trip_id = tl.trip_id) and
        self.routes->exists(r | r.route_id = tl.route_id))
```

---

## 7. Implementation Notes

### Runtime Validation

These OCL constraints are implemented as runtime checks in the code:

**booking_system_v3.py:**
```python
def book_trip(self, connection, travelers):
    # Pre-condition checks
    if not travelers:
        raise ValueError("Precondition failed: travelers->notEmpty()")
    
    # Check for duplicate travelers
    seen = set()
    for first, last, id_num, age in travelers:
        if (last, id_num) in seen:
            raise ValueError("Precondition failed: no duplicate travelers")
        seen.add((last, id_num))
    
    # Check for existing bookings
    for traveler in travelers:
        client = Client(*traveler)
        if self._has_booking_for_connection(client, connection):
            raise ValueError("Precondition failed: client already has booking")
    
    # ... execution ...
    
    # Post-condition verification
    assert trip.trip_id > 0, "Postcondition failed: trip_id must be positive"
    assert len(trip.reservations) == len(travelers), "Postcondition failed: reservation count"
```

**Reservation class:**
```python
@dataclass
class Reservation:
    client: Client
    ticket: Ticket
    
    def __post_init__(self):
        # Invariant: clientTicketMatch
        if self.ticket.client != self.client:
            raise ValueError("Invariant violated: ticket.client must match reservation.client")
```

### Testing Constraints

**test_ocl_constraints.py** validates all OCL expressions at runtime.

---

## 8. Constraint Violation Examples

### Example 1: Duplicate Traveler

```python
# Violates: travelers->forAll(t1, t2 | t1 <> t2 implies ...)
booking.book_trip(connection, [
    ("John", "Smith", "PASS001", 45),
    ("John", "Smith", "PASS001", 45)  # DUPLICATE
])
# Raises: ValueError("Precondition failed: no duplicate travelers")
```

### Example 2: Ticket-Client Mismatch

```python
# Violates: Reservation.inv clientTicketMatch
client1 = Client("John", "Smith", "PASS001", 45)
client2 = Client("Jane", "Doe", "PASS002", 42)
ticket = Ticket(1001, client1, connection, datetime.now())

reservation = Reservation(client2, ticket)  # MISMATCH
# Raises: ValueError("Invariant violated: ticket.client must match")
```

### Example 3: Invalid Layover

```python
# Violates: Itinerary.inv validLayovers
# Connection with 3-hour daytime layover
connection = network.search(..., layover_policy="strict")
# System automatically filters out invalid layovers
# No connections with 180-minute daytime layovers returned
```

---

## 9. Traceability Matrix

| OCL Constraint | Business Rule | Implementation | Test |
|----------------|---------------|----------------|------|
| book_trip pre | BR-011, BR-012 | `BookingSystem.book_trip()` | `test_duplicate_booking_prevention()` |
| Reservation.clientTicketMatch | BR-016 | `Reservation.__post_init__()` | `test_reservation_creation()` |
| Trip.hasReservations | BR-012 | `Trip.__post_init__()` | `test_trip_creation()` |
| Client.validAge | Input validation | `Client.__post_init__()` | `test_client_validation()` |
| Itinerary.validLayovers | BR-008 (FR-004) | `LayoverValidator` | `test_layover_validation()` |

---

## Document Metadata

**Version:** 1.0  
**Last Updated:** November 23, 2025  
**Compliance:** OCL 2.5 Specification  
**Purpose:** Formal constraint specification for final iteration

