"""Shared rate limiter (IP-based) for the FastAPI application.

Used by:
- ``main.py`` — infrastructure-level 120 req/min (defense in depth)
- ``public.py`` — per-endpoint 10 req/min for the public lead-magnet API
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
