#!/usr/bin/env python3
"""
Booking CLI - Iteration 2

Command-line interface for trip booking and viewing.
Extends the search CLI with booking capabilities.
"""

import argparse
import json
from typing import List
from rail_network import RailNetwork
from booking_system import BookingSystem, Trip


def print_trip_summary(trip: Trip, verbose: bool = False):
    """Print human-readable trip summary."""
    conn = trip.connection
    
    print(f"\n{'='*80}")
    print(f"Trip ID: {trip.trip_id}")
    print(f"Booked: {trip.booking_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Travelers: {trip.total_travelers()}")
    print(f"\nConnection:")
    print(f"  Route: {conn.origin} → {conn.destination}")
    print(f"  Depart: {conn.departure_time}")
    print(f"  Arrive: {conn.arrival_time}")
    print(f"  Duration: {conn.total_travel_minutes} min")
    print(f"  Stops: {len(conn.legs) - 1}")
    
    if verbose:
        print(f"\nReservations:")
        for i, res in enumerate(trip.reservations, 1):
            client = res.client
            ticket = res.ticket
            print(f"  {i}. {client.first_name} {client.last_name}")
            print(f"     Age: {client.age}, ID: {client.id_number}")
            print(f"     Ticket: #{ticket.ticket_id}")
    
    print(f"{'='*80}\n")


def print_trips_list(trips: List[Trip], title: str):
    """Print a list of trips."""
    if not trips:
        print(f"\n{title}: None")
        return
    
    print(f"\n{title}: {len(trips)} trip(s)")
    for trip in trips:
        print_trip_summary(trip, verbose=True)


def cmd_book(args, rail_network: RailNetwork, booking_system: BookingSystem):
    """
    Handle booking command.
    
    Workflow:
    1. Search for connections based on criteria
    2. Display options to user
    3. User selects connection index
    4. Enter traveler details
    5. Book trip
    """
    # Search for connections
    itineraries = rail_network.search(
        departure_city=args.departure,
        arrival_city=args.arrival,
        train_type=args.train_type,
        day_contains=args.day,
        max_stops=args.max_stops,
        min_transfer_minutes=args.min_transfer,
        travel_class=args.travel_class,
        sort_by=args.sort_by
    )
    
    if not itineraries:
        print("No connections found matching your criteria.")
        return
    
    # Display options
    print(f"\n{'='*80}")
    print(f"Found {len(itineraries)} connection(s):")
    print(f"{'='*80}")
    
    for i, it in enumerate(itineraries[:args.limit], 1):
        row = it.to_row(travel_class=args.travel_class)
        price_key = f"total_price_{args.travel_class.lower()}"
        
        print(f"\n[{i}] {it.origin} → {it.destination}")
        print(f"    Depart: {it.departure_time} | Arrive: {it.arrival_time}")
        print(f"    Duration: {it.total_travel_minutes} min | Stops: {len(it.legs)-1}")
        print(f"    Price ({args.travel_class}): €{row[price_key]:.2f}")
        print(f"    Route: {row['legs']}")
    
    # Get user selection
    print(f"\n{'='*80}")
    try:
        selection = int(input("Select connection number (or 0 to cancel): "))
        if selection == 0:
            print("Booking cancelled.")
            return
        if selection < 1 or selection > min(len(itineraries), args.limit):
            print("Invalid selection.")
            return
    except (ValueError, EOFError, KeyboardInterrupt):
        print("\nBooking cancelled.")
        return
    
    selected_connection = itineraries[selection - 1]
    
    # Get traveler details
    print(f"\n{'='*80}")
    print("Enter traveler details:")
    travelers = []
    
    try:
        num_travelers = int(input("Number of travelers: "))
        if num_travelers < 1:
            print("At least one traveler required.")
            return
        
        for i in range(num_travelers):
            print(f"\nTraveler {i+1}:")
            first = input("  First name: ").strip()
            last = input("  Last name: ").strip()
            id_num = input("  ID number: ").strip()
            age = int(input("  Age: "))
            travelers.append((first, last, id_num, age))
    
    except (ValueError, EOFError, KeyboardInterrupt):
        print("\nBooking cancelled.")
        return
    
    # Book the trip
    try:
        trip = booking_system.book_trip(selected_connection, travelers)
        print(f"\n{'='*80}")
        print("✓ Trip booked successfully!")
        print_trip_summary(trip, verbose=True)
    
    except ValueError as e:
        print(f"\n✗ Booking failed: {e}")


def cmd_view_trips(args, booking_system: BookingSystem):
    """Handle view trips command."""
    last_name = args.last_name
    id_number = args.id_number
    
    current_trips, past_trips = booking_system.get_trips_by_client(
        last_name, id_number
    )
    
    if not current_trips and not past_trips:
        print(f"\nNo trips found for {last_name} (ID: {id_number})")
        return
    
    print(f"\n{'='*80}")
    print(f"Trips for {last_name} (ID: {id_number})")
    print(f"{'='*80}")
    
    print_trips_list(current_trips, "CURRENT TRIPS")
    print_trips_list(past_trips, "PAST TRIPS")


def cmd_search(args, rail_network: RailNetwork):
    """Handle search command (original functionality)."""
    from app import to_rows, print_table
    
    its = rail_network.search(
        departure_city=args.departure,
        arrival_city=args.arrival,
        train_type=args.train_type,
        day_contains=args.day,
        max_stops=args.max_stops,
        min_transfer_minutes=args.min_transfer,
        travel_class=args.travel_class,
        sort_by=args.sort_by,
    )
    
    rows = to_rows(its, args.travel_class)
    if args.limit > 0:
        rows = rows[:args.limit]
    
    if args.format == "json":
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
    elif args.format == "table":
        print_table(rows)
    else:
        if rows:
            cols = sorted({k for r in rows for k in r.keys()})
            print(",".join(cols))
            for r in rows:
                print(",".join(str(r.get(c, "")) for c in cols))


def main():
    parser = argparse.ArgumentParser(
        description="Rail Network Booking System - Iteration 2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for connections
  %(prog)s search --csv routes.csv --from Paris --to Berlin

  # Book a trip (interactive)
  %(prog)s book --csv routes.csv --from Paris --to Berlin

  # View your trips
  %(prog)s view-trips --csv routes.csv --last-name Smith --id ABC123
        """
    )
    
    parser.add_argument("--csv", required=True, help="Path to CSV file with routes")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    subparsers.required = True
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for connections")
    search_parser.add_argument("--from", dest="departure", help="Departure city")
    search_parser.add_argument("--to", dest="arrival", help="Arrival city")
    search_parser.add_argument("--train-type", help="Filter by train type")
    search_parser.add_argument("--day", help="Day of operation contains")
    search_parser.add_argument("--max-stops", type=int, default=2, help="Max stops (0-2)")
    search_parser.add_argument("--min-transfer", type=int, default=15, help="Min transfer time (min)")
    search_parser.add_argument("--class", dest="travel_class", default="second", 
                              help="Travel class (first/second)")
    search_parser.add_argument("--sort", dest="sort_by", default="duration", 
                              choices=["duration", "price"], help="Sort by")
    search_parser.add_argument("--limit", type=int, default=50, help="Limit results")
    search_parser.add_argument("--format", default="table", choices=["json", "table", "csv"],
                              help="Output format")
    
    # Book command
    book_parser = subparsers.add_parser("book", help="Book a trip (interactive)")
    book_parser.add_argument("--from", dest="departure", required=True, help="Departure city")
    book_parser.add_argument("--to", dest="arrival", required=True, help="Arrival city")
    book_parser.add_argument("--train-type", help="Filter by train type")
    book_parser.add_argument("--day", help="Day of operation contains")
    book_parser.add_argument("--max-stops", type=int, default=2, help="Max stops (0-2)")
    book_parser.add_argument("--min-transfer", type=int, default=15, help="Min transfer time (min)")
    book_parser.add_argument("--class", dest="travel_class", default="second",
                           help="Travel class (first/second)")
    book_parser.add_argument("--sort", dest="sort_by", default="duration",
                           choices=["duration", "price"], help="Sort by")
    book_parser.add_argument("--limit", type=int, default=10, help="Limit shown results")
    
    # View trips command
    view_parser = subparsers.add_parser("view-trips", help="View your trips")
    view_parser.add_argument("--last-name", required=True, help="Client last name")
    view_parser.add_argument("--id", dest="id_number", required=True, help="Client ID number")
    
    args = parser.parse_args()
    
    # Load rail network
    rail_network = RailNetwork.from_csv(args.csv)
    
    # Global booking system (in-memory)
    # Production: Would persist to database
    booking_system = BookingSystem()
    
    # Route to command handlers
    if args.command == "search":
        cmd_search(args, rail_network)
    elif args.command == "book":
        cmd_book(args, rail_network, booking_system)
    elif args.command == "view-trips":
        cmd_view_trips(args, booking_system)


if __name__ == "__main__":
    main()

