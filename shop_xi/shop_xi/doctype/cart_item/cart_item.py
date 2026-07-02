from frappe.model.document import Document
from frappe.utils import cint, flt


class CartItem(Document):
    def before_save(self):
        self.qty = cint(self.qty)
        self.rate = flt(self.rate)
        self.amount = self.qty * self.rate
