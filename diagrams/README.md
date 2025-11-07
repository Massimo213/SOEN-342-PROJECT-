# UML Diagrams

This directory contains PlantUML source files for system diagrams.

## Files

- `class-diagram.puml` - Domain model showing classes and relationships
- `usecase-diagram.puml` - System use cases and actors
- `sequence-booking.puml` - Book Trip interaction flow
- `sequence-search.puml` - Search Connections interaction flow
- `sequence-view-trips.puml` - View Trips interaction flow

## Rendering Diagrams

### Option 1: Online (Quickest)
1. Go to [PlantUML Online Server](http://www.plantuml.com/plantuml/uml/)
2. Copy contents of `.puml` file
3. Paste and render
4. Download PNG/SVG

### Option 2: VS Code Extension
1. Install "PlantUML" extension (jebbs.plantuml)
2. Open `.puml` file
3. Press `Alt+D` (or `Cmd+D` on Mac) to preview
4. Right-click preview → Export to PNG/SVG

### Option 3: Command Line
```bash
# Install PlantUML
brew install plantuml  # macOS
# or
apt-get install plantuml  # Ubuntu

# Render all diagrams
plantuml diagrams/*.puml

# This creates PNG files in the diagrams/ directory
```

### Option 4: Docker
```bash
docker run --rm -v $(pwd)/diagrams:/data plantuml/plantuml *.puml
```

## Diagram Descriptions

### Class Diagram
Shows the domain model architecture with:
- **rail_network** package: Route catalog and search logic
- **booking_system** package: Booking domain models
- **database** package: Persistence layer
- **layover_validator** package: Time-based validation service

Key relationships:
- RailNetwork manages TrainRoutes and creates Itineraries
- BookingSystem manages Trips containing Reservations
- Each Reservation links a Client to a Ticket
- Database provides persistence for all entities

### Use Case Diagram
Displays actors and their interactions:
- **Client**: Searches connections, books trips, views trips
- **System Administrator**: Loads route records
- **Database**: Persistence backend

Includes/extends relationships show use case composition.

### Sequence Diagrams

**Booking Flow:**
1. Client initiates booking via CLI
2. System validates travelers and checks for duplicates
3. Database transaction creates trip, tickets, and trip_legs
4. Client receives confirmation with numeric trip ID

**Search Flow:**
1. Client submits search criteria
2. RailNetwork searches direct and multi-stop routes
3. LayoverValidator validates transfer times (Iteration 3)
4. Results sorted and displayed to client

**View Trips Flow:**
1. Client provides credentials (last name + ID)
2. System retrieves all trips for client from database
3. Trips categorized as current (today/future) or past
4. Formatted results displayed to client

## Notes

- All diagrams reflect **Iteration 3** architecture with database persistence
- **Changed elements** annotated in diagrams (e.g., numeric trip IDs)
- **New elements** in Iteration 3 marked with `<<Iteration 3>>` stereotype

