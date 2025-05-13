# Copyright (c) 2025, radenadri and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from inventoree.utils.naming import get_item_prefix


class Item(Document):
    def autoname(self):

        prefix = get_item_prefix(self)

        # If item_code is already set by user and has proper prefix, use it
        if self.item_code and self.item_code.startswith(prefix):
            self.name = self.item_code
            return

        # Get the next number in the series
        self.name = frappe.model.naming.make_autoname(f"{prefix}.#####")

        # Also set the item_code field
        self.item_code = self.name
