from urllib.parse import urlencode

import frappe


DEFAULT_CATEGORY_IMAGES = [
	"/assets/shop_xi/images/banner-04.jpg",
	"/assets/shop_xi/images/banner-05.jpg",
	"/assets/shop_xi/images/banner-07.jpg",
	"/assets/shop_xi/images/banner-08.jpg",
	"/assets/shop_xi/images/banner-09.jpg",
]

EXCLUDED_GROUP_FIELD = "custom_ecommerce_excluded_"
BIG_FRONT_CARD_FIELD = "custom_bigger_front_card"
SMALL_FRONT_CARD_FIELD = "custom_smaller_front_card"
ROOT_ITEM_GROUPS = {"All Item Groups", "All Item Group"}


def get_context(context):
	context.home_categories = get_home_categories()
	context.product_category_links = get_home_category_links()
	context.trendy_items = get_trendy_items()
	context.trendy_modal_products = get_modal_products(context.trendy_items)
	return context


def get_home_categories(small_limit=3):
	big_groups = get_front_card_item_groups(BIG_FRONT_CARD_FIELD)
	small_groups = get_front_card_item_groups(SMALL_FRONT_CARD_FIELD, small_limit)

	categories = []
	for group in big_groups:
		categories.append(get_category_card(group, "big"))

	for group in small_groups:
		categories.append(get_category_card(group, "small"))

	if categories:
		return categories

	return [] if get_visible_item_group_filters() else get_fallback_categories()


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
	meta = frappe.get_meta("Item")
	trendy_field = get_trendy_field(meta)
	visible_group_names = get_visible_item_group_names()

	if not trendy_field:
		return []

	if visible_group_names is not None and not visible_group_names:
		return []

	fields = [
		"name",
		"item_name",
		"item_group",
		"description",
		"image",
		"creation",
	]

	if meta.has_field("custom_image_2"):
		fields.append("custom_image_2")

	filters = {
		"disabled": 0,
		trendy_field: 1,
	}

	if visible_group_names is not None:
		filters["item_group"] = ["in", visible_group_names]

	items = frappe.get_all(
		"Item",
		fields=fields,
		filters=filters,
		order_by="modified desc",
		limit_page_length=limit,
	)

	prices = frappe.get_all(
		"Item Price",
		fields=["item_code", "price_list_rate", "custom_price_before"],
		filters={"selling": 1},
	)
	price_map = {price.item_code: price for price in prices}

	for item in items:
		price = price_map.get(item.name)
		item.selling_price = price.price_list_rate if price else None
		item.custom_price_before = price.custom_price_before if price else None

	return items


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


def get_trendy_field(meta):
	if meta.has_field("is_trendy"):
		return "is_trendy"

	if meta.has_field("custom_is_trendy"):
		return "custom_is_trendy"

	return None


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


def get_fallback_categories():
	labels = ["Women", "Men", "Watches", "Bags", "Accessories"]
	return [
		{
			"label": label,
			"image": DEFAULT_CATEGORY_IMAGES[index],
			"url": "/products?" + urlencode({"group": label}),
			"info": "Shop Collection",
		}
		for index, label in enumerate(labels)
	]
