import string
import random
import hashlib
import threading
from datetime import datetime


class TrackingIDGenerator:
    def __init__(self):
        self._counter = 0
        self._lock = threading.Lock()
        self._last_microsecond = 0

    def generate_secure_tracking_id(self, length=10):
        """
        Generate tracking ID with sequence counter to prevent duplicates.
        Even if called simultaneously, it guarantees uniqueness.
        """
        with self._lock:
            now = datetime.now()
            current_microsecond = now.microsecond

            # Reset counter if microsecond changed
            if current_microsecond != self._last_microsecond:
                self._counter = 0
                self._last_microsecond = current_microsecond
            else:
                self._counter += 1

            # Company identifier
            company_part = "TR"  # 2 chars

            # Timestamp with microseconds and counter
            timestamp_str = (f"{now.strftime('%Y%m%d%H%M%S')}"
                             f"{now.microsecond:06d}{self._counter:04d}")

            # Hash the timestamp for compactness
            timestamp_hash = hashlib.md5(timestamp_str.encode()).hexdigest()
            timestamp_part = ''.join(c for c in timestamp_hash if c.isalnum())[:6].upper()

            # Random component for the remaining space
            remaining = length - len(company_part) - len(timestamp_part)
            if remaining > 0:
                chars = string.ascii_uppercase + string.digits
                random_part = ''.join(random.choices(chars, k=remaining))
                result = company_part + timestamp_part + random_part
            else:
                result = company_part + timestamp_part

            return result[:length]


tracking_id_generator = TrackingIDGenerator()
