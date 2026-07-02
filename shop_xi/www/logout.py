import frappe


def get_context(context):
	frappe.local.login_manager.logout()
	frappe.db.commit()
	frappe.local.flags.redirect_location = "/login"
	raise frappe.Redirect
