import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address


DEFAULT_CONTACT_SETTINGS = {
	"address": "Century Mall Upstairs Table 07, corner Julius Nyerere & Nelson Mandela, Harare. Use FEDEX Entrance.",
	"phone": "+263 77 603 1280",
	"email": "Stephengandiwa01@gmail.com",
}


def get_context(context):
	settings = get_contact_settings()
	context.store_currency = frappe.defaults.get_global_default("currency") or "USD"
	context.contact_address = settings["address"]
	context.contact_phone = settings["phone"]
	context.contact_email = settings["email"]

def get_contact_settings():
	settings = DEFAULT_CONTACT_SETTINGS.copy()

	try:
		meta = frappe.get_meta("Contact Settings")
	except Exception:
		return settings

	for fieldname in ("address", "phone"):
		if meta.has_field(fieldname):
			value = frappe.db.get_single_value("Contact Settings", fieldname)
			if value:
				settings[fieldname] = value

	email_field = "email" if meta.has_field("email") else "location"
	if meta.has_field(email_field):
		value = frappe.db.get_single_value("Contact Settings", email_field)
		if value:
			settings["email"] = value

	return settings


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60)
def save_contact(email=None, phone=None, message=None):
	email = (email or "").strip()
	phone = (phone or "").strip()
	message = (message or "").strip()

	if not email:
		frappe.throw(_("Email is required"))

	if not message:
		frappe.throw(_("Message is required"))

	if len(email) > 254:
		frappe.throw(_("Email is too long"))

	if len(phone) > 50:
		frappe.throw(_("Phone number is too long"))

	if len(message) > 5000:
		frappe.throw(_("Message is too long"))

	validate_email_address(email, throw=True)

	contact = frappe.new_doc("Contact Us")
	contact.email = email
	contact.phone = phone
	contact.message = message
	contact.flags.ignore_permissions = True
	contact.insert(ignore_permissions=True)

	return {
		"status": "success",
		"name": contact.name,
		"message": _("Thank you. Your message has been sent.")
	}
