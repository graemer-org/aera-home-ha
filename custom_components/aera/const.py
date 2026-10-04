"""Constants for the Aera for Home integration."""

from datetime import timedelta
import logging

DOMAIN = "aera"
LOGGER = logging.getLogger(__package__)

SCAN_INTERVAL = timedelta(seconds=60)
REQUEST_TIMEOUT = 30

DEFAULT_SESSION_MINUTES = 60
MIN_SESSION_MINUTES = 15
MAX_SESSION_MINUTES = 240
SESSION_STEP_MINUTES = 15
