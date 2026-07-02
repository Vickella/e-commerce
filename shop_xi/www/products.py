import math
from urllib.parse import urlencode

import frappe


EXCLUDED_GROUP_FIELD = "custom_ecommerce_excluded_"
ROOT_ITEM_GROUPS = {"All Item Groups", "All Item Group"}


def get_context(context):
    page = frappe.form_dict.get("page")
    page = int(page) if page and str(page).isdigit() else 1

    page_length = 8
    group = frappe.form_dict.get("group")
    search = (frappe.form_dict.get("q") or "").strip()
    selected_sort = frappe.form_dict.get("sort") or "default"
    selected_price = frappe.form_dict.get("price") or "all"
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
    return get_product_context(page, group, (q or "").strip(), sort or "default", price or "all")


def get_product_context(page, group, search, selected_sort, selected_price, page_length=8):
    filters = {"disabled": 0}
    visible_group_names = get_visible_item_group_names()

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
        fields=[
            "name",
            "item_name",
            "item_group",
            "description",
            "image",
            "creation",
            "custom_is_trendy",
            "custom_just_arrived",
            "custom_image_2",
        ],
        filters=filters,
        or_filters=or_filters,
        order_by="item_name asc",
    )

    prices = frappe.get_all(
        "Item Price",
        fields=["item_code", "price_list_rate", "custom_price_before"],
        filters={"selling": 1},
    )
    price_map = {p.item_code: p for p in prices}

    for item in all_items:
        p = price_map.get(item.name)
        item.selling_price = p.price_list_rate if p else None
        item.custom_price_before = p.custom_price_before if p else None

    min_price, max_price = get_price_bounds(selected_price)
    if min_price is not None or max_price is not None:
        all_items = [
            item for item in all_items
            if item.selling_price is not None
            and (min_price is None or item.selling_price >= min_price)
            and (max_price is None or item.selling_price <= max_price)
        ]

    all_items = sort_items(all_items, selected_sort)

    total_items = len(all_items)
    total_pages = max(1, math.ceil(total_items / page_length))
    page = max(1, min(page, total_pages))
    items = all_items[(page - 1) * page_length:page * page_length]

    modal_products = []
    for item in items:
        images = [
            image
            for image in [item.image, item.custom_image_2]
            if image
        ] or ["/assets/shop_xi/images/product-01.jpg"]

        modal_products.append(
            {
                "name": item.name,
                "title": item.item_name or item.name,
                "price": item.selling_price,
                "description": item.description or "",
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
        if group.name not in ROOT_ITEM_GROUPS
        and group.item_group_name not in ROOT_ITEM_GROUPS
    ]


def get_visible_item_group_names():
    meta = frappe.get_meta("Item Group")

    return [group.name for group in get_visible_item_groups()]


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
        category_links.append(
            {
                "label": item_group.item_group_name,
                "url": build_url({**common_params, "group": item_group.name, "page": 1}),
                "active": item_group.name == group,
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
        return sorted(items, key=lambda item: (item.selling_price is None, item.selling_price or 0))

    if selected_sort == "price_desc":
        return sorted(items, key=lambda item: (item.selling_price is None, -(item.selling_price or 0)))

    if selected_sort == "newest":
        return sorted(items, key=lambda item: item.creation, reverse=True)

    return sorted(items, key=lambda item: (item.item_name or item.name or "").lower())
