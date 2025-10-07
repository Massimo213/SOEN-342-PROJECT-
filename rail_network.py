
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Iterable
from datetime import datetime, timedelta
import re

# ----------------------------
# Time helpers
# ----------------------------

def parse_time_to_minutes(t: str) -> int:
    """
    Parse time strings like:
      - "08:30"
      - "8:30"
      - "08"
      - "08 (+1d)"
      - "08:00(+1d)"
      - "08 (+2d)"
    Returns minutes since starting midnight, allowing day offsets via (+Nd).
    """
    if t is None:
        raise ValueError("Time is None")
    s = t.strip()
    # Extract day offset like (+1d)
    day_offset = 0
    m = re.search(r"\(\s*\+(\d+)\s*d\s*\)", s)
    if m:
        day_offset = int(m.group(1))
        s = re.sub(r"\(\s*\+\d+\s*d\s*\)", "", s).strip()

    # Extract H or H:M
    hm = re.match(r"^(\d{1,2})(?::(\d{1,2}))?$", s)
    if not hm:
        # Some datasets may include stray spaces or trailing chars, try to pull numbers
        nums = re.findall(r"\d+", s)
        if not nums:
            raise ValueError(f"Unrecognized time format: {t!r}")
        h = int(nums[0])
        mnt = int(nums[1]) if len(nums) > 1 else 0
    else:
        h = int(hm.group(1))
        mnt = int(hm.group(2)) if hm.group(2) is not None else 0

    total = h * 60 + mnt + day_offset * 24 * 60
    return total

def minutes_to_hhmm(minutes: int) -> str:
    # Represent within 0-23:59; day offsets not shown here
    minutes = minutes % (24*60)
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def duration_minutes(dep_min: int, arr_min: int) -> int:
    """
    Duration from departure minutes to arrival minutes accounting for potential day offsets.
    Assumes arr_min and dep_min may already include day offsets via parse_time_to_minutes.
    """
    if arr_min >= dep_min:
        return arr_min - dep_min
    # If arrival numerically less but intended next day (shouldn't happen with offsets), roll once
    return (arr_min + 24*60) - dep_min

# ----------------------------
# Domain models
# ----------------------------

from dataclasses import dataclass, field

@dataclass
class TrainRoute:
    route_id: str
    departure_city: str
    arrival_city: str
    departure_time: str   # as provided
    arrival_time: str     # as provided
    train_type: str
    days_of_operation: str
    first_class_rate: float
    second_class_rate: float

    dep_min: int = field(init=False)
    arr_min: int = field(init=False)
    duration_min: int = field(init=False)

    def __post_init__(self):
        self.dep_min = parse_time_to_minutes(self.departure_time)
        self.arr_min = parse_time_to_minutes(self.arrival_time)
        self.duration_min = duration_minutes(self.dep_min, self.arr_min)

@dataclass
class Leg:
    route: TrainRoute

@dataclass
class Itinerary:
    legs: List[Leg]

    @property
    def origin(self) -> str:
        return self.legs[0].route.departure_city

    @property
    def destination(self) -> str:
        return self.legs[-1].route.arrival_city

    @property
    def departure_time(self) -> str:
        return self.legs[0].route.departure_time

    @property
    def arrival_time(self) -> str:
        return self.legs[-1].route.arrival_time

    @property
    def total_travel_minutes(self) -> int:
        total = 0
        for i, leg in enumerate(self.legs):
            total += leg.route.duration_min
            if i > 0:
                prev_arr = self.legs[i-1].route.arr_min
                this_dep = leg.route.dep_min
                gap = duration_minutes(prev_arr, this_dep)
                total += gap
        return total

    @property
    def displayed_transfer_minutes(self) -> int:
        tr = 0
        for i in range(1, len(self.legs)):
            prev_arr = self.legs[i-1].route.arr_min
            this_dep = self.legs[i].route.dep_min
            tr += duration_minutes(prev_arr, this_dep)
        return tr

    def price(self, travel_class: str = "second") -> float:
        total = 0.0
        for leg in self.legs:
            if travel_class.lower().startswith("first"):
                total += leg.route.first_class_rate
            else:
                total += leg.route.second_class_rate
        return total

    def to_row(self, travel_class: str = "second") -> dict:
        return {
            "legs": " → ".join([f"{leg.route.departure_city}({leg.route.departure_time})→{leg.route.arrival_city}({leg.route.arrival_time})" for leg in self.legs]),
            "stops": max(0, len(self.legs)-1),
            "origin": self.origin,
            "destination": self.destination,
            "depart": self.departure_time,
            "arrive": self.arrival_time,
            "trip_duration(min)": self.total_travel_minutes,
            "transfer_time(min)": self.displayed_transfer_minutes,
            f"total_price_{travel_class.lower()}": self.price(travel_class)
        }

class RailNetwork:
    def __init__(self, routes: List[TrainRoute]):
        self.routes = routes
        self.index_by_origin: Dict[str, List[TrainRoute]] = {}
        for r in routes:
            self.index_by_origin.setdefault(r.departure_city.lower(), []).append(r)

    @classmethod
    def from_csv(cls, path: str) -> "RailNetwork":
        import csv
        routes: List[TrainRoute] = []
        with open(path, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                def get(*names, default=""):
                    for n in names:
                        if n in row and row[n] != "":
                            return row[n]
                    return default
                # Normalize possibly missing minutes by adding ':00' when needed
                def norm_time(x: str) -> str:
                    if x is None: return ""
                    s = str(x).strip()
                    # leave day offset text; our parser will handle it
                    # ensure HH:MM present before any offset text
                    # If matches '^\d{1,2}(\:\d{1,2})?' optionally followed by offset
                    m = re.match(r"^\s*(\d{1,2})(?::(\d{1,2}))?(\s*\(\s*\+\d+\s*d\s*\))?\s*$", s)
                    if m:
                        h = m.group(1)
                        mm = m.group(2) if m.group(2) is not None else "00"
                        off = m.group(3) or ""
                        return f"{int(h):02d}:{int(mm):02d}{off}"
                    return s
                route = TrainRoute(
                    route_id=str(get("Route ID", "route_id")).strip(),
                    departure_city=str(get("Departure City", "departure_city")).strip(),
                    arrival_city=str(get("Arrival City", "arrival_city")).strip(),
                    departure_time=norm_time(get("Departure Time", "departure_time")),
                    arrival_time=norm_time(get("Arrival Time", "arrival_time")),
                    train_type=str(get("Train Type", "train_type")).strip(),
                    days_of_operation=str(get("Days of Operation", "days_of_operation")).strip(),
                    first_class_rate=float(str(get("First Class ticket rate (in euro)", "first_class_rate", default="0") or "0").strip()),
                    second_class_rate=float(str(get("Second Class ticket rate (in euro)", "second_class_rate", default="0") or "0").strip()),
                )
                routes.append(route)
        return cls(routes)

    def search(
        self,
        departure_city: Optional[str] = None,
        arrival_city: Optional[str] = None,
        train_type: Optional[str] = None,
        day_contains: Optional[str] = None,
        max_stops: int = 2,
        min_transfer_minutes: int = 15,
        travel_class: str = "second",
        sort_by: str = "duration",
    ) -> List[Itinerary]:
        results: List[Itinerary] = []

        for r in self.routes:
            if not self._match(r, departure_city, arrival_city, train_type, day_contains):
                continue
            results.append(Itinerary(legs=[Leg(r)]))

        if max_stops >= 1 and departure_city and arrival_city:
            results.extend(self._build_one_stop(departure_city, arrival_city, train_type, day_contains, min_transfer_minutes))
        if max_stops >= 2 and departure_city and arrival_city:
            results.extend(self._build_two_stops(departure_city, arrival_city, train_type, day_contains, min_transfer_minutes))

        def legs_key(it: Itinerary):
            return tuple((leg.route.route_id for leg in it.legs))
        seen = set()
        unique: List[Itinerary] = []
        for it in results:
            k = legs_key(it)
            if k not in seen:
                seen.add(k)
                unique.append(it)

        if sort_by == "price":
            unique.sort(key=lambda it: it.price(travel_class))
        else:
            unique.sort(key=lambda it: it.total_travel_minutes)

        return unique

    def _match(self, r: TrainRoute, dep_city, arr_city, train_type, day_contains) -> bool:
        if dep_city and r.departure_city.lower() != dep_city.lower():
            return False
        if arr_city and r.arrival_city.lower() != arr_city.lower():
            return False
        if train_type and r.train_type.lower() != train_type.lower():
            return False
        if day_contains and day_contains.lower() not in r.days_of_operation.lower():
            return False
        return True

    def _build_one_stop(self, dep_city, arr_city, train_type, day_contains, min_transfer_minutes) -> List[Itinerary]:
        its: List[Itinerary] = []
        dep_routes = [r for r in self.routes if self._match(r, dep_city, None, train_type, day_contains)]
        for r1 in dep_routes:
            mid = r1.arrival_city
            for r2 in self.index_by_origin.get(mid.lower(), []):
                if not self._match(r2, mid, arr_city, train_type, day_contains):
                    continue
                if self._transfer_gap_ok(r1, r2, min_transfer_minutes):
                    its.append(Itinerary(legs=[Leg(r1), Leg(r2)]))
        return its

    def _build_two_stops(self, dep_city, arr_city, train_type, day_contains, min_transfer_minutes) -> List[Itinerary]:
        its: List[Itinerary] = []
        dep_routes = [r for r in self.routes if self._match(r, dep_city, None, train_type, day_contains)]
        for r1 in dep_routes:
            mid1 = r1.arrival_city
            for r2 in self.index_by_origin.get(mid1.lower(), []):
                if not self._match(r2, mid1, None, train_type, day_contains):
                    continue
                if not self._transfer_gap_ok(r1, r2, min_transfer_minutes):
                    continue
                mid2 = r2.arrival_city
                for r3 in self.index_by_origin.get(mid2.lower(), []):
                    if not self._match(r3, mid2, arr_city, train_type, day_contains):
                        continue
                    if self._transfer_gap_ok(r2, r3, min_transfer_minutes):
                        its.append(Itinerary(legs=[Leg(r1), Leg(r2), Leg(r3)]))
        return its

    def _transfer_gap_ok(self, r_prev, r_next, min_transfer_minutes) -> bool:
        gap = r_next.dep_min - r_prev.arr_min
        if gap < 0:
            gap += 24*60
        return gap >= min_transfer_minutes
