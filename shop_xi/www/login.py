from urllib.parse import quote, urlparse

import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.rate_limiter import rate_limit
from frappe.utils import cint
from frappe.utils.data import escape_html
from frappe.utils.html_utils import get_icon_html
from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys, redirect_post_login
from frappe.utils.password import get_decrypted_password


no_cache = True


@frappe.whitelist(allow_guest=True)
def custom_login(email, password, redirect_to=None):
	try:
		login_manager = LoginManager()
		login_manager.authenticate(user=email, pwd=password)
		login_manager.post_login()
		frappe.db.commit()

		return {
			"status": "Success",
			"message": "Logged in",
			"redirect_to": sanitize_redirect(redirect_to) or "/",
		}
	except Exception as exc:
		frappe.clear_messages()
		return {
			"status": "Error",
			"message": str(exc),
		}


def get_context(context):
	redirect_to = sanitize_redirect(frappe.local.request.args.get("redirect-to")) or "/"

	if frappe.session.user != "Guest":
		frappe.local.flags.redirect_location = redirect_to
		raise frappe.Redirect

	context.no_header = True
	context.no_cache = True
	context.title = "Login"
	context.hide_login = True
	context.redirect_to = redirect_to
	context.signup_url = "/signup?redirect-to=" + quote(redirect_to, safe="/")
	context.back_to_label = "Back to checkout" if redirect_to.startswith("/shopping-cart") else "Back to shop"
	context.disable_user_pass_login = cint(frappe.get_system_settings("disable_user_pass_login"))
	context.login_with_email_link = frappe.get_system_settings("login_with_email_link")
	context.provider_logins = get_provider_logins(redirect_to)
	context.social_login = bool(context.provider_logins)

	return context


def get_provider_logins(redirect_to):
	provider_logins = []
	providers = frappe.get_all(
		"Social Login Key",
		filters={"enable_social_login": 1},
		fields=["name", "client_id", "base_url", "provider_name", "icon"],
		order_by="name",
	)

	for provider in providers:
		client_secret = get_decrypted_password(
			"Social Login Key",
			provider.name,
			"client_secret",
			raise_exception=False,
		)
		if not client_secret:
			continue

		icon = None
		if provider.icon:
			if provider.provider_name == "Custom":
				icon = get_icon_html(provider.icon, small=True)
			else:
				icon = f"<img src={escape_html(provider.icon)!r} alt={escape_html(provider.provider_name)!r}>"

		if provider.client_id and provider.base_url and get_oauth_keys(provider.name):
			provider_logins.append(
				{
					"name": provider.name,
					"provider_name": provider.provider_name,
					"auth_url": get_oauth2_authorize_url(provider.name, redirect_to),
					"icon": icon,
				}
			)

	return provider_logins


@frappe.whitelist(allow_guest=True)
def login_via_token(login_token: str):
	sid = frappe.cache.get_value(f"login_token:{login_token}", expires=True)
	if not sid:
		frappe.respond_as_web_page(_("Invalid Request"), _("Invalid Login Token"), http_status_code=417)
		return

	frappe.local.form_dict.sid = sid
	frappe.local.login_manager = LoginManager()
	redirect_post_login(
		desk_user=frappe.db.get_value("User", frappe.session.user, "user_type") == "System User"
	)


def get_login_with_email_link_ratelimit() -> int:
	return frappe.get_system_settings("rate_limit_email_link_login") or 5


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=get_login_with_email_link_ratelimit, seconds=60 * 60)
def send_login_link(email: str):
	if not frappe.get_system_settings("login_with_email_link"):
		return

	frappe.get_attr("frappe.www.login.send_login_link")(email)


def sanitize_redirect(redirect: str | None) -> str | None:
	if not redirect:
		return redirect

	parsed_redirect = urlparse(redirect)
	parsed_request_host = urlparse(frappe.local.request.url)

	if parsed_redirect.netloc and parsed_redirect.netloc != parsed_request_host.netloc:
		return "/"

	return parsed_redirect.geturl()
