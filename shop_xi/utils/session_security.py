"""
Session Security Module for Shop Xi E-commerce
Provides cryptographically secure guest session management to prevent cart spoofing.
"""

import hashlib
import hmac
import logging
from typing import Optional, Tuple

import frappe

logger = logging.getLogger(__name__)

# Session configuration
SESSION_EXPIRY_SECONDS = 2592000  # 30 days
SESSION_CACHE_PREFIX = "shop_xi_guest_session:"
SIGNING_KEY = (frappe.conf.get("encryption_key") or frappe.generate_hash(length=32)).encode()


def generate_guest_session(guest_id: str) -> str:
	"""
	Generate a cryptographically secure guest session token.

	Args:
		guest_id: The guest identifier (typically UUID)

	Returns:
		str: HMAC-SHA256 signed session hash safe to store in client cookies

	Raises:
		ValueError: If guest_id is empty or invalid
	"""
	if not guest_id or not isinstance(guest_id, str):
		raise ValueError("Invalid guest_id provided")

	if len(guest_id) > 100:
		raise ValueError("Guest ID exceeds maximum length")

	try:
		# Create HMAC-SHA256 signature of guest_id
		signature = hmac.new(
			SIGNING_KEY.encode() if isinstance(SIGNING_KEY, str) else SIGNING_KEY,
			guest_id.encode(),
			hashlib.sha256
		).hexdigest()

		# Store the token in cache with expiration
		cache_key = f"{SESSION_CACHE_PREFIX}{signature}"
		frappe.cache.set_value(cache_key, guest_id, expires_in_sec=SESSION_EXPIRY_SECONDS)

		logger.info(f"Generated session token for guest: {guest_id[:8]}...")
		return signature

	except Exception as e:
		logger.error(f"Failed to generate guest session: {str(e)}")
		raise frappe.ValidationError(f"Could not create session: {str(e)}")


def validate_guest_session(session_hash: str, guest_id: str) -> bool:
	"""
	Validate a guest session token against the provided guest_id.

	Args:
		session_hash: The session hash (returned from generate_guest_session)
		guest_id: The guest identifier to validate against

	Returns:
		bool: True if session is valid and matches guest_id, False otherwise
	"""
	if not session_hash or not guest_id:
		return False

	try:
		cache_key = f"{SESSION_CACHE_PREFIX}{session_hash}"
		cached_guest_id = frappe.cache.get_value(cache_key)

		# Timing-safe comparison to prevent timing attacks
		is_valid = cached_guest_id is not None and hmac.compare_digest(
			cached_guest_id,
			guest_id
		)

		if not is_valid:
			logger.warning(f"Invalid session validation attempt for guest: {guest_id[:8]}...")

		return is_valid

	except Exception as e:
		logger.error(f"Error validating session: {str(e)}")
		return False


def refresh_guest_session(session_hash: str) -> bool:
	"""
	Refresh a guest session to extend expiration time.
	Useful for keeping active carts available longer.

	Args:
		session_hash: The session hash to refresh

	Returns:
		bool: True if refresh succeeded, False otherwise
	"""
	try:
		cache_key = f"{SESSION_CACHE_PREFIX}{session_hash}"
		guest_id = frappe.cache.get_value(cache_key)

		if not guest_id:
			return False

		# Re-set with new expiration
		frappe.cache.set_value(cache_key, guest_id, expires_in_sec=SESSION_EXPIRY_SECONDS)
		return True

	except Exception:
		return False


def invalidate_guest_session(session_hash: str) -> None:
	"""
	Explicitly invalidate a guest session (logout).

	Args:
		session_hash: The session hash to invalidate
	"""
	try:
		cache_key = f"{SESSION_CACHE_PREFIX}{session_hash}"
		frappe.cache.delete_value(cache_key)
		logger.info(f"Invalidated guest session: {session_hash[:8]}...")
	except Exception as e:
		logger.error(f"Error invalidating session: {str(e)}")
