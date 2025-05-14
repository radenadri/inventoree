# Copyright (c) 2025, radenadri and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class StockLedgerEntry(Document):
    def autoname(self):
        """
        Generate a unique name for the Stock Ledger Entry
        """
        self.name = make_autoname("SLE-.#####")

    def validate(self):
        """
        Validate the Stock Ledger Entry
        """
        self.validate_mandatory()
        self.validate_item()
        self.validate_warehouse()

    def validate_mandatory(self):
        """
        Validate mandatory fields
        """
        mandatory = [
            "item_code",
            "warehouse",
            "posting_date",
            "posting_time",
            "voucher_type",
            "voucher_no",
        ]

        for field in mandatory:
            if not self.get(field):
                frappe.throw(_(f"{frappe.unscrub(field)} is required"))

    def validate_item(self):
        """
        Validate that the item exists and is a stock item
        """
        if not frappe.db.exists("Item", self.item_code):
            frappe.throw(_(f"Item {self.item_code} does not exist"))

        if not frappe.db.get_value("Item", self.item_code, "is_stock_item"):
            frappe.throw(_(f"Item {self.item_code} is not a stock item"))

    def validate_warehouse(self):
        """
        Validate that the warehouse exists
        """
        if not frappe.db.exists("Warehouse", self.warehouse):
            frappe.throw(_(f"Warehouse {self.warehouse} does not exist"))

    def on_submit(self):
        """
        Update related records when a Stock Ledger Entry is submitted
        """
        # Stock Ledger Entries are typically created by other documents (like Stock Entry)
        # So we don't need to update Bin here, but we can add additional validations or actions
        pass

    def on_cancel(self):
        """
        Update related records when a Stock Ledger Entry is cancelled
        """
        # Stock Ledger Entries are typically cancelled by other documents
        # So we don't need to update Bin here, but we can add additional validations or actions
        pass
