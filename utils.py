import bech32
import binascii
import logging
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

def normalize_pubkey(pubkey):
    """Convert a pubkey from either hex or bech32 format to hex format"""
    if not pubkey:
        return None

    # If already hex format
    if len(pubkey) == 64 and all(c in '0123456789abcdefABCDEF' for c in pubkey):
        return pubkey.lower()

    # Try bech32 conversion if starts with npub
    if pubkey.startswith('npub'):
        try:
            hrp, data = bech32.bech32_decode(pubkey)
            if hrp != 'npub' or data is None:
                return None
            raw_pubkey = bytes(bech32.convertbits(data, 5, 8, False))
            return binascii.hexlify(raw_pubkey).decode('utf-8')
        except Exception as e:
            logger.error(f"Error converting bech32 pubkey: {e}")
            return None

    return None

def pubkey_to_bech32(hex_pubkey):
    """Convert a hex pubkey to bech32 format"""
    try:
        raw_pubkey = binascii.unhexlify(hex_pubkey)
        data = bech32.convertbits(raw_pubkey, 8, 5)
        return bech32.bech32_encode('npub', data)
    except Exception as e:
        logger.error(f"Error converting hex to bech32: {e}")
        return None

def parse_time_filter(time_str):
    """Parse time filter string into Unix timestamp

    Supports:
    - Unix timestamps
    - Relative time strings (e.g., '1day', '1week', '1month')

    Returns:
    - Unix timestamp (integer) or None if invalid
    """
    if not time_str:
        return None

    try:
        # Try parsing as integer timestamp first
        timestamp = int(time_str)
        return timestamp
    except ValueError:
        pass

    # Parse relative time strings
    time_units = {
        'minute': 60,
        'hour': 3600,
        'day': 86400,
        'week': 604800,
        'month': 2592000  # 30 days
    }

    try:
        # Extract number and unit
        for unit, seconds in time_units.items():
            if time_str.endswith(unit):
                number = int(time_str.replace(unit, ''))
                # Calculate timestamp
                now = int(time.time())
                return now - (number * seconds)
    except ValueError:
        pass

    logger.warning(f"Invalid time filter format: {time_str}")
    return None