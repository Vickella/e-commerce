import importlib.util
import sys
import types
import unittest
from pathlib import Path


class FakeCache:
    def __init__(self):
        self.store = {}

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value

    def get_value(self, key):
        return self.store.get(key)

    def delete_value(self, key):
        self.store.pop(key, None)


class FakeDB:
    def __init__(self):
        self.values = {('Item', 'SKU-1', 'standard_rate'): 99.5}

    def get_value(self, doctype, name, field, as_dict=False):
        if (doctype, name, field) in self.values:
            value = self.values[(doctype, name, field)]
            if as_dict:
                return {field: value}
            return value
        return None

    def count(self, doctype, filters=None):
        return 0


class FakeFrappe(types.SimpleNamespace):
    conf = {"encryption_key": "test-encryption-key"}
    cache = FakeCache()
    session = types.SimpleNamespace(user="Guest")
    form_dict = {}
    local = types.SimpleNamespace(request=None)

    @staticmethod
    def generate_hash(length=32):
        return "x" * length

    class ValidationError(Exception):
        pass

    class PermissionError(Exception):
        pass

    class SessionExpiredError(Exception):
        pass

    @staticmethod
    def throw(msg, exc=None):
        raise (exc or ValueError)(msg)

    @staticmethod
    def get_all(doctype, fields=None, filters=None, order_by=None, limit_page_length=None):
        if doctype == "Item Price":
            return []
        if doctype == "Item":
            return [{"name": "SKU-1", "standard_rate": 99.5}]
        return []

    @staticmethod
    def get_doc(*args, **kwargs):
        return None

    @staticmethod
    def get_meta(*args, **kwargs):
        return types.SimpleNamespace(has_field=lambda *a, **kw: False)

    @staticmethod
    def whitelist(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    db = FakeDB()


frappe_mod = FakeFrappe()
sys.modules["frappe"] = frappe_mod
frappe_utils = types.ModuleType("frappe.utils")
frappe_utils.cint = lambda value: int(value)
frappe_utils.flt = lambda value: float(value)
frappe_utils.nowdate = lambda: "2026-10-09"
sys.modules["frappe.utils"] = frappe_utils

shop_xi_pkg = types.ModuleType("shop_xi")
shop_xi_pkg.__path__ = []
shop_xi_utils_pkg = types.ModuleType("shop_xi.utils")
shop_xi_utils_pkg.__path__ = []
shop_xi_www_pkg = types.ModuleType("shop_xi.www")
shop_xi_www_pkg.__path__ = []
sys.modules["shop_xi"] = shop_xi_pkg
sys.modules["shop_xi.utils"] = shop_xi_utils_pkg
sys.modules["shop_xi.www"] = shop_xi_www_pkg

session_security_mod = types.ModuleType("shop_xi.utils.session_security")
session_security_mod.validate_guest_session = lambda *args, **kwargs: True
session_security_mod.generate_guest_session = lambda guest_id: "session_hash"
sys.modules["shop_xi.utils.session_security"] = session_security_mod


class TestCartPriceFallback(unittest.TestCase):
    def load_cart_module(self):
        file_path = Path(__file__).resolve().parents[1] / "www" / "cart.py"
        spec = importlib.util.spec_from_file_location("shop_xi.www.cart", file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["shop_xi.www.cart"] = module
        spec.loader.exec_module(module)
        return module

    def test_get_item_selling_price_uses_standard_rate_when_item_price_missing(self):
        module = self.load_cart_module()
        self.assertEqual(module.get_item_selling_price("SKU-1"), 99.5)

    def test_get_identity_prefers_authenticated_user_over_guest_id(self):
        module = self.load_cart_module()
        module.frappe.session.user = "Administrator"
        self.assertEqual(module.get_identity("guest-123"), "Administrator")

    def test_get_identity_for_guest_user_uses_guest_id(self):
        module = self.load_cart_module()
        module.frappe.session.user = "Guest"
        self.assertEqual(module.get_identity("guest-123"), "guest-123")

    def test_merge_cart_on_login_moves_guest_items_to_user_cart(self):
        module = self.load_cart_module()
        module.frappe.session.user = "test@example.com"

        class GuestItem:
            def __init__(self, name, item, qty):
                self.name = name
                self.item = item
                self.qty = qty

        guest_items = [GuestItem("g1", "SKU-1", 2)]
        module.frappe.get_all = lambda *args, **kwargs: guest_items
        module.frappe.db.get_value = lambda *args, **kwargs: None

        class FakeDoc:
            def __init__(self, item, qty, rate):
                self.item = item
                self.qty = qty
                self.rate = rate
                self.cart_owner = None
                self.inserted = False

            def save(self):
                return None

            def insert(self):
                self.inserted = True
                return self

        created = []

        def fake_new_doc(doctype):
            doc = FakeDoc("SKU-1", 2, 99.5)
            created.append(doc)
            return doc

        module.frappe.new_doc = fake_new_doc
        module.frappe.delete_doc = lambda doctype, name: None
        module.frappe.db.commit = lambda: None
        module.frappe.db.rollback = lambda: None
        module.frappe.request = types.SimpleNamespace(cookies={"guest_id": "guest-123"})

        class LoginManager:
            user = "test@example.com"

        module.merge_cart_on_login(LoginManager())
        self.assertEqual(created[0].item, "SKU-1")
        self.assertEqual(created[0].qty, 2)


if __name__ == "__main__":
    unittest.main()
