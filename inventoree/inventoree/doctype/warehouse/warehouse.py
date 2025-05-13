# Copyright (c) 2025, radenadri and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Warehouse(Document):
    def get_title(self):
        return self.warehouse_name or self.name
