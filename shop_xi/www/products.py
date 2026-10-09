import math
import re
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import frappe

logger = logging.getLogger(__name__)
no_cache = True

EXCLUDED_GROUP_FIELD = "custom_ecommerce_excluded_"
ROOT_ITEM_GROUPS = {"All Item Groups", "All Item Group"}


# ============================================================================
# HELPER: Get auto-publish groups from settings
# ============================================================================

def get_auto_publish_groups() -> List[str]:
	"""
	Get list of item groups configured for auto-publishing.

	Returns:
		list: Item group names, or empty list if not configured
	"""
	try:
		settings = frappe.get_doc("Ecommerce Settings")

		if not settings.auto_publish_enabled:
			return []

		groups = []
		if hasattr(settings, 'auto_publish_groups') and settings.auto_publish_groups:
			groups = [row.item_group for row in settings.auto_publish_groups if row.item_group]

		return groups
	except frappe.DoesNotExistError:
		return []
	except Exception as e:
		logger.error(f"Error getting auto-publish groups: {str(e)}")
		return []


def batch_get_item_prices(item_codes: List[str]) -> Dict[str, float]:
	"""
	Fetch prices for multiple items in ONE database query (Performance Fix #4).

	Falls back to the Item's standard rate when Item Price records are missing or
	when the project does not populate the selling flag consistently.

	Args:
		item_codes: List of item codes

	Returns:
		dict: Map of {item_code: price}
	"""
	if not item_codes:
		return {}

	unique_item_codes = list(dict.fromkeys(item_codes))

	try:
		prices = frappe.get_all(
			"Item Price",
			fields=["item_code", "price_list_rate"],
			filters={"item_code": ["in", unique_item_codes]},
			order_by="modified desc",
		)

		price_map = {}
		for price in prices:
			item_code = price.get("item_code") if isinstance(price, dict) else getattr(price, "item_code", None)
			price_list_rate = price.get("price_list_rate") if isinstance(price, dict) else getattr(price, "price_list_rate", None)
			if item_code and item_code not in price_map:
				price_map[item_code] = frappe.utils.flt(price_list_rate)

		missing_codes = [code for code in unique_item_codes if code not in price_map]
		if missing_codes:
			items = frappe.get_all(
				"Item",
				fields=["name", "standard_rate"],
				filters={"name": ["in", missing_codes]},
			)
			for item in items:
				item_name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
				standard_rate = item.get("standard_rate") if isinstance(item, dict) else getattr(item, "standard_rate", None)
				if item_name and item_name not in price_map and standard_rate is not None:
					price_map[item_name] = frappe.utils.flt(standard_rate)

		return price_map
	except Exception as e:
		logger.error(f"Error fetching prices: {str(e)}")
		return {}


def get_context(context):
    context.no_cache = True
    request_args = frappe.local.request.args if frappe.local.request else frappe.form_dict
    page = request_args.get("page")
    page = int(page) if page and str(page).isdigit() else 1

    page_length = 8
    context.store_currency = frappe.defaults.get_global_default("currency") or "USD"
    group = resolve_item_group(request_args.get("group"))
    search = (request_args.get("q") or "").strip()
    selected_sort = request_args.get("sort") or "default"
    selected_price = request_args.get("price") or "all"
    product_context = get_product_context(page, group, search, selected_sort, selected_price, page_length)
    item_groups = get_visible_item_groups()

    context.update(product_context)
    context.item_groups = item_groups
    context.category_links = build_category_links(
        item_groups,
        group,
        {
            "q": search,
            "sort": selected_sort if selected_sort != "default" else None,
            "price": selected_price if selected_price != "all" else None,
        },
    )

    return context


@frappe.whitelist(allow_guest=True)
def search_products(q="", group="", sort="default", price="all", page=1):
    page = int(page) if page and str(page).isdigit() else 1
    return get_product_context(page, resolve_item_group(group), (q or "").strip(), sort or "default", price or "all")


def get_product_context(page, group, search, selected_sort, selected_price, page_length=8):
    group = resolve_item_group(group)
    filters = {"disabled": 0}
    visible_group_names = get_visible_item_group_names()
    item_fields = [
        "name",
        "item_name",
        "item_group",
        "description",
        "image",
        "creation",
    ]
    if frappe.get_meta("Item").has_field("custom_image_2"):
        item_fields.append("custom_image_2")

    # If a specific group is requested, filter by that group
    if group:
        if visible_group_names is not None and group not in visible_group_names:
            return get_empty_product_context(page, group, search, selected_sort, selected_price)
        filters["item_group"] = group
    # If no group specified, load all products (don't filter by visibility)
    # This ensures "All Products" shows items by default

    or_filters = None
    if search:
        search_text = f"%{search}%"
        or_filters = [
            ["Item", "name", "like", search_text],
            ["Item", "item_name", "like", search_text],
            ["Item", "description", "like", search_text],
        ]

    all_items = frappe.get_all(
        "Item",
        fields=item_fields,
        filters=filters,
        or_filters=or_filters,
        order_by="item_name asc",
    )

    # PERFORMANCE FIX #4: Batch fetch all prices in ONE query instead of N+1
    item_codes = [item.get("name") if isinstance(item, dict) else getattr(item, "name", None) for item in all_items]
    price_map = batch_get_item_prices(item_codes)

    for item in all_items:
        item_name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
        p = price_map.get(item_name)
        if isinstance(item, dict):
            item["selling_price"] = p if p else None
            item["custom_price_before"] = None
        else:
            item.selling_price = p if p else None
            item.custom_price_before = None

    min_price, max_price = get_price_bounds(selected_price)
    if min_price is not None or max_price is not None:
        all_items = [
            item for item in all_items
            if ((item.get("selling_price") if isinstance(item, dict) else getattr(item, "selling_price", None)) is not None)
            and (min_price is None or (item.get("selling_price") if isinstance(item, dict) else getattr(item, "selling_price", None)) >= min_price)
            and (max_price is None or (item.get("selling_price") if isinstance(item, dict) else getattr(item, "selling_price", None)) <= max_price)
        ]

    all_items = sort_items(all_items, selected_sort)

    total_items = len(all_items)
    total_pages = max(1, math.ceil(total_items / page_length))
    page = max(1, min(page, total_pages))
    items = all_items[(page - 1) * page_length:page * page_length]

    modal_products = []
    for item in items:
        item_name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
        item_title = (item.get("item_name") if isinstance(item, dict) else getattr(item, "item_name", None)) or item_name
        item_description = (item.get("description") if isinstance(item, dict) else getattr(item, "description", None)) or ""
        images = [
            image
            for image in [
                item.get("image") if isinstance(item, dict) else getattr(item, "image", None),
                item.get("custom_image_2") if isinstance(item, dict) else getattr(item, "custom_image_2", None),
            ]
            if image
        ] or ["/assets/shop_xi/images/product-01.jpg"]

        modal_products.append(
            {
                "name": item_name,
                "title": item_title,
                "price": getattr(item, "selling_price", None) if not isinstance(item, dict) else item.get("selling_price"),
                "description": item_description,
                "images": images,
            }
        )

    page_params = {
        "group": group,
        "q": search,
        "sort": selected_sort if selected_sort != "default" else None,
        "price": selected_price if selected_price != "all" else None,
    }

    sort_options = [
        {"label": "Default", "value": "default"},
        {"label": "Newest", "value": "newest"},
        {"label": "Price: Low to High", "value": "price_asc"},
        {"label": "Price: High to Low", "value": "price_desc"},
    ]

    price_options = [
        {"label": "All", "value": "all"},
        {"label": "$0.00 - $50.00", "value": "0-50"},
        {"label": "$50.00 - $100.00", "value": "50-100"},
        {"label": "$100.00 - $150.00", "value": "100-150"},
        {"label": "$150.00 - $200.00", "value": "150-200"},
        {"label": "$200.00+", "value": "200-plus"},
    ]

    for option in sort_options:
        option["active"] = option["value"] == selected_sort
        option["url"] = build_url({**page_params, "sort": option["value"], "page": 1})

    for option in price_options:
        option["active"] = option["value"] == selected_price
        option["url"] = build_url({**page_params, "price": option["value"], "page": 1})

    pages = [
        {
            "number": page_no,
            "url": build_url({**page_params, "page": page_no}),
            "active": page_no == page,
        }
        for page_no in range(1, total_pages + 1)
    ]

    return {
        "items": items,
        "modal_products": modal_products,
        "sort_options": sort_options,
        "price_options": price_options,
        "pages": pages,
        "current_page": page,
        "total_pages": total_pages,
        "selected_group": group,
        "search": search,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_url": build_url({**page_params, "page": page - 1}),
        "next_url": build_url({**page_params, "page": page + 1}),
        "show_pagination": total_pages > 1,
    }


def get_visible_item_group_filters():
    filters = {}
    meta = frappe.get_meta("Item Group")

    if meta.has_field("custom_disabled"):
        filters["custom_disabled"] = 0

    if meta.has_field(EXCLUDED_GROUP_FIELD):
        filters[EXCLUDED_GROUP_FIELD] = 0

    return filters


def get_visible_item_groups():
    item_groups = frappe.get_all(
        "Item Group",
        fields=["name", "item_group_name", "image"],
        filters=get_visible_item_group_filters(),
        order_by="item_group_name asc",
    )
    return [
        group for group in item_groups
        if (group.get("name") if isinstance(group, dict) else getattr(group, "name", None)) not in ROOT_ITEM_GROUPS
        and (group.get("item_group_name") if isinstance(group, dict) else getattr(group, "item_group_name", None)) not in ROOT_ITEM_GROUPS
    ]


def get_visible_item_group_names():
    return [(group.get("name") if isinstance(group, dict) else getattr(group, "name", None)) for group in get_visible_item_groups()]


def normalize_group_key(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def resolve_item_group(group):
    group = (group or "").strip()

    if not group:
        return ""

    item_groups = get_visible_item_groups()
    group_key = normalize_group_key(group)

    for item_group in item_groups:
        group_name = item_group.get("name") if isinstance(item_group, dict) else getattr(item_group, "name", None)
        group_label = item_group.get("item_group_name") if isinstance(item_group, dict) else getattr(item_group, "item_group_name", None)
        candidates = {
            group_name,
            group_label,
        }

        normalized_candidates = {normalize_group_key(candidate) for candidate in candidates}

        if group_key in normalized_candidates:
            return group_name

        if any(
            group_key and (group_key in candidate or candidate in group_key)
            for candidate in normalized_candidates
        ):
            return group_name

    return group


def get_empty_product_context(page, group, search, selected_sort, selected_price):
    page_params = {
        "group": group,
        "q": search,
        "sort": selected_sort if selected_sort != "default" else None,
        "price": selected_price if selected_price != "all" else None,
    }

    return {
        "items": [],
        "modal_products": [],
        "sort_options": get_sort_options(page_params, selected_sort),
        "price_options": get_price_options(page_params, selected_price),
        "pages": [],
        "current_page": 1,
        "total_pages": 1,
        "selected_group": group,
        "search": search,
        "has_prev": False,
        "has_next": False,
        "prev_url": build_url({**page_params, "page": 1}),
        "next_url": build_url({**page_params, "page": 1}),
        "show_pagination": False,
    }


def get_sort_options(page_params, selected_sort):
    sort_options = [
        {"label": "Default", "value": "default"},
        {"label": "Newest", "value": "newest"},
        {"label": "Price: Low to High", "value": "price_asc"},
        {"label": "Price: High to Low", "value": "price_desc"},
    ]

    for option in sort_options:
        option["active"] = option["value"] == selected_sort
        option["url"] = build_url({**page_params, "sort": option["value"], "page": 1})

    return sort_options


def get_price_options(page_params, selected_price):
    price_options = [
        {"label": "All", "value": "all"},
        {"label": "$0.00 - $50.00", "value": "0-50"},
        {"label": "$50.00 - $100.00", "value": "50-100"},
        {"label": "$100.00 - $150.00", "value": "100-150"},
        {"label": "$150.00 - $200.00", "value": "150-200"},
        {"label": "$200.00+", "value": "200-plus"},
    ]

    for option in price_options:
        option["active"] = option["value"] == selected_price
        option["url"] = build_url({**page_params, "price": option["value"], "page": 1})

    return price_options


def build_url(params):
    clean_params = {key: value for key, value in params.items() if value not in (None, "")}
    return f"?{urlencode(clean_params)}" if clean_params else "?page=1"


def build_category_links(item_groups, group, common_params):
    category_links = [
        {
            "label": "All Products",
            "url": build_url({**common_params, "page": 1}),
            "active": not group,
        }
    ]

    for item_group in item_groups:
        group_name = item_group.get("name") if isinstance(item_group, dict) else getattr(item_group, "name", None)
        group_label = item_group.get("item_group_name") if isinstance(item_group, dict) else getattr(item_group, "item_group_name", None)
        category_links.append(
            {
                "label": group_label,
                "url": build_url({**common_params, "group": group_name, "page": 1}),
                "active": group_name == group,
            }
        )

    return category_links


def get_price_bounds(price_filter):
    ranges = {
        "0-50": (0, 50),
        "50-100": (50, 100),
        "100-150": (100, 150),
        "150-200": (150, 200),
        "200-plus": (200, None),
    }

    return ranges.get(price_filter, (None, None))


def sort_items(items, selected_sort):
    if selected_sort == "price_asc":
        return sorted(items, key=lambda item: ((item.get("selling_price") if isinstance(item, dict) else getattr(item, "selling_price", None)) is None, (item.get("selling_price") if isinstance(item, dict) else getattr(item, "selling_price", None)) or 0))

    if selected_sort == "price_desc":
        return sorted(items, key=lambda item: ((item.get("selling_price") if isinstance(item, dict) else getattr(item, "selling_price", None)) is None, -((item.get("selling_price") if isinstance(item, dict) else getattr(item, "selling_price", None)) or 0)))

    if selected_sort == "newest":
        return sorted(items, key=lambda item: item.get("creation") if isinstance(item, dict) else getattr(item, "creation", None), reverse=True)

    return sorted(items, key=lambda item: ((item.get("item_name") if isinstance(item, dict) else getattr(item, "item_name", None)) or (item.get("name") if isinstance(item, dict) else getattr(item, "name", None)) or "").lower())
