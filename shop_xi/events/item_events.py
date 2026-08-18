"""
Item Event Handlers for Shop Xi E-commerce
Automatically publishes items to the website based on ecommerce settings.
"""

import logging
from typing import Optional

import frappe

logger = logging.getLogger(__name__)


def get_auto_publish_groups() -> list:
	"""
	Retrieve list of item groups configured for auto-publishing.

	Returns:
		list: List of item group names to auto-publish
	"""
	try:
		settings = frappe.get_doc("Ecommerce Settings")

		if not settings.auto_publish_enabled:
			return []

		# An empty group list means all item groups, matching the settings description.
		groups = [
			row.item_group
			for row in (getattr(settings, "auto_publish_groups", None) or [])
			if row.item_group
		]

		return groups

	except frappe.DoesNotExistError:
		logger.warning("Ecommerce Settings not found, auto-publish disabled")
		return []
	except Exception as e:
		logger.error(f"Error fetching auto-publish groups: {str(e)}")
		return []


def should_auto_publish(item_group: Optional[str]) -> bool:
	"""
	Determine if an item should be auto-published based on its group.

	Args:
		item_group: The item's item_group

	Returns:
		bool: True if item should be auto-published
	"""
	if not item_group:
		return False

	auto_publish_groups = get_auto_publish_groups()
	return not auto_publish_groups or item_group in auto_publish_groups


def mark_item_published(item_doc) -> None:
	"""
	Mark an item as published to website by setting web_item custom field.
	Uses Frappe's website_item_group mechanism if available.

	Args:
		item_doc: The Item document to mark as published
	"""
	try:
		# Try standard Frappe "Show in Website" field if it exists
		meta = frappe.get_meta("Item")

		# Check for website visibility fields
		if meta.has_field("show_in_website") and not item_doc.show_in_website:
			item_doc.db_set("show_in_website", 1, update_modified=False)
			logger.info("Marked item %s as show_in_website=1", item_doc.name)

		if meta.has_field("web_long_description") or meta.has_field("website_item_group"):
			# Item has website fields, ensure it's visible
			if hasattr(item_doc, 'disabled') and item_doc.disabled:
				logger.warning(f"Item {item_doc.name} is disabled, cannot auto-publish")
				return

			logger.info(f"Item {item_doc.name} configured for website visibility")

	except Exception as e:
		logger.error(f"Error marking item {item_doc.name} as published: {str(e)}")


def after_item_insert(doc, method=None):
	"""
	Hook called after an Item is inserted.
	Auto-publishes the item if its item_group is in auto_publish_groups.

	Args:
		doc: The Item document
		method: The method name (unused, required by hook interface)
	"""
	try:
		if doc.disabled:
			logger.debug(f"Item {doc.name} is disabled, skipping auto-publish")
			return

		if should_auto_publish(doc.item_group):
			mark_item_published(doc)
			logger.info(f"Auto-published item {doc.name} from group {doc.item_group}")
		else:
			logger.debug(f"Item {doc.name} group {doc.item_group} not in auto-publish list")

	except Exception as e:
		logger.error(f"Error in after_item_insert hook for {doc.name}: {str(e)}")
		# Don't raise - don't block item creation if auto-publish fails


def after_item_update(doc, method=None):
	"""
	Hook called after an Item is updated.
	Auto-publishes the item if:
	1. It wasn't published before but should be now
	2. Its item_group changed to an auto-publish group

	Args:
		doc: The Item document
		method: The method name (unused, required by hook interface)
	"""
	try:
		if doc.disabled:
			logger.debug(f"Item {doc.name} is disabled, skipping auto-publish")
			return

		if should_auto_publish(doc.item_group):
			if frappe.get_meta("Item").has_field("show_in_website") and not doc.show_in_website:
				mark_item_published(doc)
				logger.info("Auto-published updated item %s from group %s", doc.name, doc.item_group)

	except Exception as e:
		logger.error(f"Error in after_item_update hook for {doc.name}: {str(e)}")
		# Don't raise - don't block item update if auto-publish fails


def on_item_group_change(doc, method=None):
	"""
	Optional hook for Item Group updates - could trigger re-publishing of all items in that group.

	Args:
		doc: The Item Group document
		method: The method name (unused, required by hook interface)
	"""
	try:
		logger.debug(f"Item Group {doc.name} updated")
		# Future enhancement: re-evaluate all items in this group

	except Exception as e:
		logger.error(f"Error in item_group change handler: {str(e)}")
