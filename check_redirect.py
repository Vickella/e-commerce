import frappe

print("home_page:", frappe.db.get_value("Website Settings", "Website Settings", "home_page"))

redirects = frappe.get_all("Website Route Redirect", fields=["name", "source", "target"])
print("redirects:", redirects)

pages = frappe.get_all("Web Page", filters={"route": ["in", ["", "/"]]}, fields=["name", "route", "published"])
print("web_pages_root:", pages)
