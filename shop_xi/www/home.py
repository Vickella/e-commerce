from urllib.parse import urlencode
import logging
from typing import List, Dict, Optional

import frappe

logger = logging.getLogger(__name__)

LANDING_HERO_IMAGES = [
	"/assets/shop_xi/images/ganz6.webp",
	"/assets/shop_xi/images/ganz7.webp",
	"/assets/shop_xi/images/ganz8.webp",
	"/assets/shop_xi/images/hero-shoe-01.png",
	"/assets/shop_xi/images/hero-shoe-02.png",
	"/assets/shop_xi/images/hero-shoe-03.webp",
	"/assets/shop_xi/images/hero-shoe-04.png",
	"/assets/shop_xi/images/hero-shoe-05.png",
	"/assets/shop_xi/images/hero-shoe-06.png",
	"/assets/shop_xi/images/hero-shoe-07.jpeg",
	"/assets/shop_xi/images/hero-shoe-08.jpeg",
	"/assets/shop_xi/images/hero-shoe-09.jpeg",
	"/assets/shop_xi/images/hero-shoe-10.png",
]
LANDING_PRODUCT_IMAGES = [
	"/assets/shop_xi/images/ganz9.webp",
	"/assets/shop_xi/images/ganz10.webp",
	"/assets/shop_xi/images/ganz1.webp",
	"/assets/shop_xi/images/ganz2.webp",
]
LANDING_HERO_COPY = [
	("Made for the moments that matter.", "Find a pair that moves with your day.", "Explore footwear"),
	("A sharper step starts here.", "Everyday pairs, elevated with intention.", "Shop the edit"),
	("The finish changes everything.", "Distinctive footwear for Harare streets and beyond.", "See the collection"),
	("Comfort, with a point of view.", "Built to be worn often and remembered.", "Discover your pair"),
	("Your next signature pair.", "Premium energy, grounded in everyday wear.", "Shop footwear"),
]

EXCLUDED_GROUP_FIELD = "custom_ecommerce_excluded_"
BIG_FRONT_CARD_FIELD = "custom_bigger_front_card"
SMALL_FRONT_CARD_FIELD = "custom_smaller_front_card"
ROOT_ITEM_GROUPS = {"All Item Groups", "All Item Group"}


# ============================================================================
# HELPER: Batch price fetching (Performance Fix #4)
# ============================================================================

def batch_get_item_prices(item_codes: List[str]) -> Dict[str, float]:
	"""
	Fetch prices for multiple items in ONE database query.

	Args:
		item_codes: List of item codes

	Returns:
		dict: Map of {item_code: price}
	"""
	if not item_codes:
		return {}

	try:
		prices = frappe.get_all(
			"Item Price",
			fields=["item_code", "price_list_rate"],
			filters={
				"item_code": ["in", item_codes],
				"selling": 1
			},
			order_by="modified desc"
		)

		price_map = {}
		for price in prices:
			if price.item_code not in price_map:
				price_map[price.item_code] = frappe.utils.flt(price.price_list_rate)

		return price_map
	except Exception as e:
		logger.error(f"Error fetching prices: {str(e)}")
		return {}


def get_context(context):
	context.store_currency = frappe.defaults.get_global_default("currency") or "USD"
	context.home_categories = get_home_categories()
	context.product_category_links = get_home_category_links()
	context.trendy_items = get_trendy_items()
	context.trendy_modal_products = get_modal_products(context.trendy_items)
	context.landing_hero_images = LANDING_HERO_IMAGES
	context.landing_hero_copy = LANDING_HERO_COPY
	context.landing_product_images = LANDING_PRODUCT_IMAGES
	return context


def get_home_categories(small_limit=3):
	big_groups = get_front_card_item_groups(BIG_FRONT_CARD_FIELD)
	small_groups = get_front_card_item_groups(SMALL_FRONT_CARD_FIELD, small_limit)

	categories = []
	for group in big_groups:
		categories.append(get_category_card(group, "big"))

	for group in small_groups:
		categories.append(get_category_card(group, "small"))

	return categories


def get_home_category_links(limit=50):
	categories = get_visible_item_groups(limit=limit)
	return [{"label": "All Products", "url": "/products"}] + [
		{
			"label": category.item_group_name or category.name,
			"url": "/products?" + urlencode({"group": category.name}),
		}
		for category in categories
	]


def get_trendy_items(limit=8):
	"""
	Get recently added/modified items to display on homepage.
	Simplified version - no 'trendy' field required.

	Args:
		limit: Number of items to fetch (default: 8)

	Returns:
		list: Recent items with pricing
	"""
	try:
		visible_group_names = get_visible_item_group_names()

		fields = [
			"name",
			"item_name",
			"item_group",
			"description",
			"image",
			"creation",
		]

		if frappe.get_meta("Item").has_field("custom_image_2"):
			fields.append("custom_image_2")

		filters = {
			"disabled": 0,
		}

		# Only show items from visible groups if configured
		if visible_group_names is not None and visible_group_names:
			filters["item_group"] = ["in", visible_group_names]

		items = frappe.get_all(
			"Item",
			fields=fields,
			filters=filters,
			order_by="modified desc",
			limit_page_length=limit,
		)

		if not items:
			return []

		# PERFORMANCE FIX #4: Batch fetch all prices in ONE query instead of N+1
		item_codes = [item.name for item in items]
		price_map = batch_get_item_prices(item_codes)

		for item in items:
			price = price_map.get(item.name)
			item.selling_price = price if price else None
			item.custom_price_before = None

		return items

	except Exception as e:
		logger.error(f"Error fetching trendy items: {str(e)}")
		return []


def get_visible_item_group_filters():
	filters = {}
	meta = frappe.get_meta("Item Group")

	if meta.has_field("custom_disabled"):
		filters["custom_disabled"] = 0

	if meta.has_field(EXCLUDED_GROUP_FIELD):
		filters[EXCLUDED_GROUP_FIELD] = 0

	return filters


def get_visible_item_groups(limit=None):
	query = {
		"doctype": "Item Group",
		"fields": ["name", "item_group_name", "image"],
		"filters": get_visible_item_group_filters(),
		"order_by": "item_group_name asc",
	}
	if limit:
		query["limit_page_length"] = limit

	item_groups = frappe.get_all(**query)
	return [
		group for group in item_groups
		if group.name not in ROOT_ITEM_GROUPS
		and group.item_group_name not in ROOT_ITEM_GROUPS
	]


def get_front_card_item_groups(fieldname, limit=None):
	meta = frappe.get_meta("Item Group")

	if not meta.has_field(fieldname):
		return []

	filters = get_visible_item_group_filters()
	filters[fieldname] = 1

	query = {
		"doctype": "Item Group",
		"fields": ["name", "item_group_name", "image"],
		"filters": filters,
		"order_by": "item_group_name asc",
	}
	if limit:
		query["limit_page_length"] = limit

	item_groups = frappe.get_all(**query)
	return [
		group for group in item_groups
		if group.name not in ROOT_ITEM_GROUPS
		and group.item_group_name not in ROOT_ITEM_GROUPS
	]


def get_category_card(group, card_size):
	return {
		"label": group.item_group_name or group.name,
		"image": group.image,
		"url": "/products?" + urlencode({"group": group.name}),
		"info": "Shop Collection",
		"card_size": card_size,
	}


def get_visible_item_group_names():
	return [group.name for group in get_visible_item_groups()]


def get_modal_products(items):
	products = []

	for item in items:
		images = [
			image
			for image in [
				item.image,
				item.get("custom_image_2"),
			]
			if image
		] or ["/assets/shop_xi/images/product-01.jpg"]

		products.append(
			{
				"name": item.name,
				"title": item.item_name or item.name,
				"price": item.selling_price,
				"description": item.description or "",
				"images": images,
			}
		)

	return products





