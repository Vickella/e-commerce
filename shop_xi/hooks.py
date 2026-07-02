app_name = "shop_xi"
app_title = "Shop Xi"
app_publisher = "munyaradzi chirove"
app_description = "frappe ecommerce"
app_email = "chirovemunyaradzi@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "shop_xi",
# 		"logo": "/assets/shop_xi/logo.png",
# 		"title": "Shop Xi",
# 		"route": "/shop_xi",
# 		"has_permission": "shop_xi.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/shop_xi/css/shop_xi.css"
# app_include_js = "/assets/shop_xi/js/shop_xi.js"

# include js, css files in header of web template
# web_include_css = "/assets/shop_xi/css/shop_xi.css"
# web_include_js = "/assets/shop_xi/js/shop_xi.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "shop_xi/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "shop_xi/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
home_page = "home"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "shop_xi.utils.jinja_methods",
# 	"filters": "shop_xi.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "shop_xi.install.before_install"
# after_install = "shop_xi.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "shop_xi.uninstall.before_uninstall"
# after_uninstall = "shop_xi.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "shop_xi.utils.before_app_install"
# after_app_install = "shop_xi.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "shop_xi.utils.before_app_uninstall"
# after_app_uninstall = "shop_xi.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "shop_xi.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"shop_xi.tasks.all"
# 	],
# 	"daily": [
# 		"shop_xi.tasks.daily"
# 	],
# 	"hourly": [
# 		"shop_xi.tasks.hourly"
# 	],
# 	"weekly": [
# 		"shop_xi.tasks.weekly"
# 	],
# 	"monthly": [
# 		"shop_xi.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "shop_xi.install.before_tests"

fixtures = [
	{
		"doctype": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Item Group-custom_ecommerce_excluded_",
					"Item Group-custom_bigger_front_card",
					"Item Group-custom_smaller_front_card",
				],
			]
		],
	}
]

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "shop_xi.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "shop_xi.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["shop_xi.utils.before_request"]
# after_request = ["shop_xi.utils.after_request"]

# Job Events
# ----------
# before_job = ["shop_xi.utils.before_job"]
# after_job = ["shop_xi.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"shop_xi.auth.validate"
# ]

on_login = "shop_xi.www.cart.merge_cart_on_login"

override_doctype_class = {
	"Cart Item": "shop_xi.shop_xi.doctype.cart_item.cart_item.CartItem"
}

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
