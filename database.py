"""
Database Module - Iteration 3

Provides persistent storage for routes, clients, trips, and tickets using SQLite.
Replaces in-memory storage from Iterations 1-2.

Design principles:
- Raw SQL for performance transparency
- Context managers for transaction safety
- Auto-commit on success, rollback on error
- Foreign key constraints enabled
- WAL mode for concurrency
"""

import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import csv


class Database:
    """
    Database abstraction layer for Rail Network Booking System.
    
    Responsibilities:
    - Schema management (CREATE TABLE statements)
    - Connection pooling (via context manager)
    - CRUD operations for all entities
    - Query optimization via indices
    
    Thread-safety: NOT thread-safe by default.
    For multi-threaded access, use connection per thread or add locking.
    """
    
    def __init__(self, db_path: str = "booking.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file.
                     Use ":memory:" for testing.
        """
        self.db_path = db_path
        self._persistent_conn = None
        
        # For :memory: databases, keep connection open
        if self.db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(self.db_path)
            self._persistent_conn.row_factory = sqlite3.Row
            self._persistent_conn.execute("PRAGMA foreign_keys = ON")
        
        self._init_schema()
    
    @contextmanager
    def connection(self):
        """
        Context manager for database connections.
        
        Usage:
            with db.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
        
        Auto-commits on success, rolls back on exception.
        """
        # For :memory:, reuse persistent connection
        if self._persistent_conn is not None:
            try:
                yield self._persistent_conn
                self._persistent_conn.commit()
            except Exception:
                self._persistent_conn.rollback()
                raise
            return
        
        # For file-based DB, create new connection
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        
        # Enable foreign keys (SQLite default is OFF)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode = WAL")
        
        # Set busy timeout (5 seconds)
        conn.execute("PRAGMA busy_timeout = 5000")
        
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        """
        Create all tables and indices if they don't exist.
        
        Idempotent: safe to call multiple times.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Routes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routes (
                    route_id TEXT PRIMARY KEY,
                    departure_city TEXT NOT NULL,
                    arrival_city TEXT NOT NULL,
                    departure_time TEXT NOT NULL,
                    arrival_time TEXT NOT NULL,
                    train_type TEXT,
                    days_of_operation TEXT,
                    first_class_rate REAL NOT NULL DEFAULT 0.0,
                    second_class_rate REAL NOT NULL DEFAULT 0.0
                )
            """)
            
            # Indices for route search
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_routes_departure 
                ON routes(departure_city)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_routes_arrival 
                ON routes(arrival_city)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_routes_train_type 
                ON routes(train_type)
            """)
            
            # Clients table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    id_number TEXT NOT NULL,
                    age INTEGER NOT NULL CHECK(age >= 0),
                    UNIQUE(last_name, id_number)
                )
            """)
            
            # Index for client lookup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_clients_lookup 
                ON clients(last_name, id_number)
            """)
            
            # Trips table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_timestamp TEXT NOT NULL,
                    departure_city TEXT NOT NULL,
                    arrival_city TEXT NOT NULL,
                    departure_time TEXT NOT NULL,
                    arrival_time TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trips_booking 
                ON trips(booking_timestamp)
            """)
            
            # Trip legs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trip_legs (
                    trip_leg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    route_id TEXT NOT NULL,
                    leg_order INTEGER NOT NULL,
                    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE,
                    FOREIGN KEY (route_id) REFERENCES routes(route_id),
                    UNIQUE(trip_id, leg_order)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trip_legs_trip 
                ON trip_legs(trip_id, leg_order)
            """)
            
            # Tickets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    trip_id INTEGER NOT NULL,
                    issue_timestamp TEXT NOT NULL,
                    FOREIGN KEY (client_id) REFERENCES clients(client_id),
                    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tickets_client 
                ON tickets(client_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tickets_trip 
                ON tickets(trip_id)
            """)
    
    # ============ Routes Operations ============
    
    def load_routes_from_csv(self, csv_path: str) -> int:
        """
        Load routes from CSV file into database.
        
        Args:
            csv_path: Path to CSV file
        
        Returns:
            Number of routes loaded
        
        Raises:
            FileNotFoundError: If CSV doesn't exist
            ValueError: If CSV format invalid
        """
        count = 0
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing routes (for reload scenario)
            cursor.execute("DELETE FROM routes")
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cursor.execute("""
                        INSERT INTO routes (
                            route_id, departure_city, arrival_city,
                            departure_time, arrival_time, train_type,
                            days_of_operation, first_class_rate, second_class_rate
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('Route ID', row.get('route_id', '')).strip(),
                        row.get('Departure City', row.get('departure_city', '')).strip(),
                        row.get('Arrival City', row.get('arrival_city', '')).strip(),
                        row.get('Departure Time', row.get('departure_time', '')).strip(),
                        row.get('Arrival Time', row.get('arrival_time', '')).strip(),
                        row.get('Train Type', row.get('train_type', '')).strip(),
                        row.get('Days of Operation', row.get('days_of_operation', '')).strip(),
                        float(row.get('First Class ticket rate (in euro)', row.get('first_class_rate', 0)) or 0),
                        float(row.get('Second Class ticket rate (in euro)', row.get('second_class_rate', 0)) or 0)
                    ))
                    count += 1
        
        return count
    
    def get_all_routes(self) -> List[Dict]:
        """Retrieve all routes from database."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM routes")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_route_by_id(self, route_id: str) -> Optional[Dict]:
        """Get single route by ID."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM routes WHERE route_id = ?", (route_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ============ Client Operations ============
    
    def get_or_create_client(self, first_name: str, last_name: str, 
                             id_number: str, age: int) -> int:
        """
        Get existing client or create new one.
        
        Args:
            first_name, last_name, id_number, age: Client attributes
        
        Returns:
            client_id (integer)
        
        Business rule: Clients deduplicated by (last_name, id_number).
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Check if client exists
            cursor.execute("""
                SELECT client_id FROM clients 
                WHERE LOWER(last_name) = LOWER(?) AND id_number = ?
            """, (last_name, id_number))
            
            row = cursor.fetchone()
            if row:
                return row['client_id']
            
            # Create new client
            cursor.execute("""
                INSERT INTO clients (first_name, last_name, id_number, age)
                VALUES (?, ?, ?, ?)
            """, (first_name, last_name, id_number, age))
            
            return cursor.lastrowid
    
    def get_client_by_credentials(self, last_name: str, id_number: str) -> Optional[int]:
        """
        Find client by credentials.
        
        Returns:
            client_id if found, None otherwise
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT client_id FROM clients 
                WHERE LOWER(last_name) = LOWER(?) AND id_number = ?
            """, (last_name, id_number))
            row = cursor.fetchone()
            return row['client_id'] if row else None
    
    def get_client_by_id(self, client_id: int) -> Optional[Dict]:
        """Get client by ID."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ============ Trip Operations ============
    
    def create_trip(self, departure_city: str, arrival_city: str,
                    departure_time: str, arrival_time: str) -> int:
        """
        Create a new trip.
        
        Args:
            departure_city, arrival_city, departure_time, arrival_time: Connection details
        
        Returns:
            trip_id (integer, auto-increment)
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trips (booking_timestamp, departure_city, arrival_city,
                                   departure_time, arrival_time)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                departure_city,
                arrival_city,
                departure_time,
                arrival_time
            ))
            return cursor.lastrowid
    
    def get_trip_by_id(self, trip_id: int) -> Optional[Dict]:
        """Get trip by ID."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_trips_for_client(self, client_id: int) -> List[Dict]:
        """
        Get all trips for a client.
        
        Returns list of trip dictionaries.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT t.* FROM trips t
                JOIN tickets tk ON t.trip_id = tk.trip_id
                WHERE tk.client_id = ?
                ORDER BY t.booking_timestamp DESC
            """, (client_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ============ Trip Legs Operations ============
    
    def add_trip_leg(self, trip_id: int, route_id: str, leg_order: int):
        """
        Add a leg to a trip.
        
        Args:
            trip_id: Trip identifier
            route_id: Route identifier
            leg_order: 0-indexed position (0=first leg, 1=second, etc.)
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trip_legs (trip_id, route_id, leg_order)
                VALUES (?, ?, ?)
            """, (trip_id, route_id, leg_order))
    
    def get_trip_legs(self, trip_id: int) -> List[Dict]:
        """
        Get all legs for a trip, ordered by leg_order.
        
        Returns list of route dictionaries.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.* FROM routes r
                JOIN trip_legs tl ON r.route_id = tl.route_id
                WHERE tl.trip_id = ?
                ORDER BY tl.leg_order ASC
            """, (trip_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ============ Ticket Operations ============
    
    def create_ticket(self, client_id: int, trip_id: int) -> int:
        """
        Create a ticket for a client on a trip.
        
        Returns:
            ticket_id (integer, auto-increment)
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tickets (client_id, trip_id, issue_timestamp)
                VALUES (?, ?, ?)
            """, (client_id, trip_id, datetime.now().isoformat()))
            return cursor.lastrowid
    
    def get_tickets_for_trip(self, trip_id: int) -> List[Dict]:
        """Get all tickets for a trip."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tk.*, c.first_name, c.last_name, c.id_number, c.age
                FROM tickets tk
                JOIN clients c ON tk.client_id = c.client_id
                WHERE tk.trip_id = ?
            """, (trip_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_tickets_for_client(self, client_id: int) -> List[Dict]:
        """Get all tickets for a client."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tickets WHERE client_id = ?
                ORDER BY issue_timestamp DESC
            """, (client_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ============ Utility Methods ============
    
    def clear_all_data(self):
        """
        Clear all data from database (keep schema).
        
        WARNING: Destructive operation. Use for testing only.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tickets")
            cursor.execute("DELETE FROM trip_legs")
            cursor.execute("DELETE FROM trips")
            cursor.execute("DELETE FROM clients")
            cursor.execute("DELETE FROM routes")
    
    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics."""
        with self.connection() as conn:
            cursor = conn.cursor()
            stats = {}
            for table in ['routes', 'clients', 'trips', 'trip_legs', 'tickets']:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()['count']
            return stats

