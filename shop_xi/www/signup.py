from urllib.parse import quote

import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address

from shop_xi.www.login import sanitize_redirect


no_cache = True


def get_context(context):
	redirect_to = sanitize_redirect(frappe.local.request.args.get("redirect-to")) or "/"

	if frappe.session.user != "Guest":
		frappe.local.flags.redirect_location = redirect_to
		raise frappe.Redirect

	context.no_header = True
	context.no_cache = True
	context.title = "Create Account"
	context.hide_login = True
	context.redirect_to = redirect_to
	context.login_url = "/login?redirect-to=" + quote(redirect_to, safe="/")
	context.disable_signup = False

	return context


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=20, seconds=60 * 60)
def create_account(full_name, email, password, confirm_password, redirect_to=None):
	try:
		full_name = (full_name or "").strip()
		email = (email or "").strip().lower()
		password = password or ""
		confirm_password = confirm_password or ""
		redirect_to = sanitize_redirect(redirect_to) or "/"

		if not full_name:
			return error_response(_("Enter your full name."))

		if not validate_email_address(email):
			return error_response(_("Enter a valid email address."))

		if not password:
			return error_response(_("Enter a password."))

		if password != confirm_password:
			return error_response(_("Passwords do not match."))

		if frappe.db.exists("User", email):
			return error_response(_("An account already exists for this email. Please log in."))

		user = create_website_user(full_name, email, password)
		customer = get_or_create_customer(user.name)

		frappe.local.login_manager = LoginManager()
		frappe.local.login_manager.login_as(user.name)
		frappe.db.commit()

		return {
			"status": "Success",
			"message": _("Account created."),
			"redirect_to": redirect_to,
			"customer": customer,
		}
	except Exception as exc:
		frappe.db.rollback()
		frappe.clear_messages()
		return error_response(str(exc))


def create_website_user(full_name, email, password):
	first_name, last_name = split_full_name(full_name)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"enabled": 1,
			"new_password": password,
			"send_welcome_email": 0,
			"user_type": "Website User",
		}
	)
	user.flags.ignore_permissions = True
	user.flags.no_welcome_mail = True
	user.insert(ignore_permissions=True)

	default_role = frappe.get_single_value("Portal Settings", "default_role")
	if default_role:
		user.add_roles(default_role)

	return user


def get_or_create_customer(user):
	user_doc = frappe.get_doc("User", user)
	user_email = user_doc.email or user_doc.name
	customer = frappe.db.get_value("Customer", {"email_id": user_email}, "name")

	if customer:
		return customer

	customer = frappe.new_doc("Customer")
	customer.customer_name = user_doc.full_name or user_email
	customer.customer_type = "Individual"

	if customer.meta.has_field("email_id"):
		customer.email_id = user_email
	if customer.meta.has_field("customer_group"):
		customer.customer_group = get_default_customer_group()
	if customer.meta.has_field("territory"):
		customer.territory = get_default_territory()

	customer.insert(ignore_permissions=True)
	return customer.name


def get_default_customer_group():
	return (
		frappe.db.get_value("Customer Group", {"name": "Individual", "is_group": 0}, "name")
		or frappe.db.get_value("Customer Group", {"is_group": 0}, "name", order_by="lft asc")
	)


def get_default_territory():
	return (
		frappe.db.get_value("Territory", {"name": "All Territories", "is_group": 0}, "name")
		or frappe.db.get_value("Territory", {"is_group": 0}, "name", order_by="lft asc")
	)


def split_full_name(full_name):
	parts = full_name.split()
	first_name = parts[0] if parts else full_name
	last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
	return first_name, last_name


def error_response(message):
	return {
		"status": "Error",
		"message": message,
	}
