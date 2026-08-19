import frappe

print("installed_apps:", frappe.get_installed_apps())
print("home_page hooks:", frappe.get_hooks("home_page"))
print("website_route_rules:", frappe.get_hooks("website_route_rules"))

from frappe.website.path_resolver import PathResolver
resolver = PathResolver("")
try:
    page = resolver.resolve()
    print("resolved page:", page)
except Exception as e:
    print("resolve error:", e)
