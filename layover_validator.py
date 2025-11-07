"""
Layover Validator - Iteration 3

Implements time-based layover policies to avoid unreasonable connection times.

Business Rules (FR-004):
- Daytime layovers (06:00-22:00): 15-120 minutes acceptable
- After-hours layovers (22:00-06:00): 15-30 minutes acceptable

Design rationale:
- Long daytime layovers are acceptable (passengers can wait comfortably)
- After-hours layovers should be short (stations may be closed, safety concerns)
"""

from typing import Tuple


class LayoverValidator:
    """
    Service class for validating layover durations based on time of day.
    
    Stateless: All methods are pure functions.
    Thread-safe: No shared state.
    """
    
    # Configuration constants
    DAY_START = 6 * 60      # 06:00 in minutes
    DAY_END = 22 * 60       # 22:00 in minutes
    
    # Daytime policy (06:00-22:00)
    DAYTIME_MIN = 15        # minutes
    DAYTIME_MAX = 120       # minutes (2 hours)
    
    # After-hours policy (22:00-06:00)
    NIGHT_MIN = 15          # minutes
    NIGHT_MAX = 30          # minutes
    
    @classmethod
    def is_layover_acceptable(
        cls,
        arrival_minutes: int,
        departure_minutes: int,
        policy: str = "strict"
    ) -> Tuple[bool, str]:
        """
        Validate layover duration based on time-of-day context.
        
        Args:
            arrival_minutes: Arrival time at transfer station (minutes since midnight)
                            May include day offset (e.g., 1440 for next day)
            departure_minutes: Departure time of connecting train (minutes since midnight)
            policy: "strict" (default) or "lenient"
                   lenient mode allows longer layovers (up to 3 hours)
        
        Returns:
            (is_valid, reason) tuple
            - is_valid: True if layover acceptable, False otherwise
            - reason: "OK" if valid, error message otherwise
        
        Examples:
            >>> LayoverValidator.is_layover_acceptable(600, 690, "strict")
            (True, "OK")  # 90-minute daytime layover
            
            >>> LayoverValidator.is_layover_acceptable(1380, 1410, "strict")
            (True, "OK")  # 30-minute after-hours layover
            
            >>> LayoverValidator.is_layover_acceptable(600, 780, "strict")
            (False, "Layover too long: 180 min (max: 120 min for daytime)")
            
            >>> LayoverValidator.is_layover_acceptable(1380, 1425, "strict")
            (False, "Layover too long: 45 min (max: 30 min for after-hours)")
        """
        # Calculate layover duration
        if departure_minutes >= arrival_minutes:
            gap = departure_minutes - arrival_minutes
        else:
            # Handle day rollover
            gap = (24 * 60 - arrival_minutes) + departure_minutes
        
        # Normalize arrival time to 0-1439 range for time-of-day classification
        arrival_time_of_day = arrival_minutes % (24 * 60)
        
        # Determine if layover occurs during day or night
        is_daytime = cls.DAY_START <= arrival_time_of_day < cls.DAY_END
        
        # Select policy limits
        if policy == "lenient":
            min_gap = cls.DAYTIME_MIN
            max_gap = 180 if is_daytime else cls.NIGHT_MAX
        else:  # strict
            if is_daytime:
                min_gap = cls.DAYTIME_MIN
                max_gap = cls.DAYTIME_MAX
            else:
                min_gap = cls.NIGHT_MIN
                max_gap = cls.NIGHT_MAX
        
        # Validate layover duration
        if gap < min_gap:
            return False, f"Layover too short: {gap} min (min: {min_gap} min)"
        
        if gap > max_gap:
            time_context = "daytime" if is_daytime else "after-hours"
            return False, f"Layover too long: {gap} min (max: {max_gap} min for {time_context})"
        
        return True, "OK"
    
    @classmethod
    def validate_multi_stop_connection(
        cls,
        leg_times: list[Tuple[int, int]],  # [(arr1, dep1), (arr2, dep2), ...]
        policy: str = "strict"
    ) -> Tuple[bool, str]:
        """
        Validate all layovers in a multi-stop connection.
        
        Args:
            leg_times: List of (arrival_minutes, departure_minutes) tuples
                      One tuple per transfer point
            policy: "strict" or "lenient"
        
        Returns:
            (is_valid, reason) tuple
            If any layover invalid, returns False with reason for first failure
        
        Example:
            >>> times = [(540, 600), (720, 750)]  # Two transfers
            >>> LayoverValidator.validate_multi_stop_connection(times, "strict")
            (True, "OK")
        """
        for i, (arr_min, dep_min) in enumerate(leg_times):
            is_valid, reason = cls.is_layover_acceptable(arr_min, dep_min, policy)
            if not is_valid:
                return False, f"Transfer {i+1}: {reason}"
        
        return True, "OK"
    
    @classmethod
    def get_policy_description(cls, policy: str = "strict") -> str:
        """
        Get human-readable description of layover policy.
        
        Returns:
            Multi-line string describing policy rules
        """
        if policy == "lenient":
            return f"""Layover Policy (Lenient Mode):
- Daytime (06:00-22:00): {cls.DAYTIME_MIN}-180 minutes
- After-hours (22:00-06:00): {cls.NIGHT_MIN}-{cls.NIGHT_MAX} minutes
"""
        else:
            return f"""Layover Policy (Strict Mode):
- Daytime (06:00-22:00): {cls.DAYTIME_MIN}-{cls.DAYTIME_MAX} minutes
- After-hours (22:00-06:00): {cls.NIGHT_MIN}-{cls.NIGHT_MAX} minutes
"""


# Convenience function for backward compatibility
def is_layover_acceptable(
    arrival_minutes: int,
    departure_minutes: int,
    policy: str = "strict"
) -> Tuple[bool, str]:
    """
    Standalone function wrapper for LayoverValidator.
    
    Allows imports like:
        from layover_validator import is_layover_acceptable
    """
    return LayoverValidator.is_layover_acceptable(
        arrival_minutes, departure_minutes, policy
    )

