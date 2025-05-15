# Copyright (c) 2025, radenadri and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, nowdate, nowtime
from frappe.model.document import Document
from inventoree.utils.naming import get_stock_entry_prefix
from inventoree.inventoree.actions.stock_ledger_entry_actions import (
    update_stock_ledger_entry,
    update_bin,
)


class StockEntry(Document):
    def autoname(self):
        prefix = get_stock_entry_prefix(self)

        # Get the next number in the series
        self.name = frappe.model.naming.make_autoname(f"{prefix}.#####")

    def validate(self):
        """
        Validate the Stock Entry
        """
        self.validate_posting_date_time()
        self.validate_warehouses()
        self.validate_items()
        self.validate_stock_availability()
        self.calculate_totals()
        self.set_status()

    def on_change(doc, method):
        """Actions on change"""

        # Dijalankan saat status berubah
        # frappe.msgprint(f"Status changed to {doc.status}")

        if doc.status == "Submitted" and doc.entry_type == "Receipt":
            # Create Stock Ledger Entries
            update_stock_ledger_entry(doc)

            # Update Bin records
            update_bin(doc)

    def on_cancel(doc, method):
        """Actions on cancel"""
        update_stock_ledger_entry(doc, is_cancelled=1)
        update_bin(doc)

    def validate_posting_date_time(self):
        """
        Validate posting date and time
        """
        if not self.posting_date:
            self.posting_date = nowdate()

        if not self.posting_time:
            self.posting_time = nowtime()

    def validate_warehouses(self):
        """
        Validate warehouses based on entry_type
        """
        if self.entry_type in ["Issue", "Transfer"] and not self.from_warehouse:
            frappe.throw(
                _("From Warehouse is required for {0}").format(self.entry_type)
            )

        if self.entry_type in ["Receipt", "Transfer"] and not self.to_warehouse:
            frappe.throw(_("To Warehouse is required for {0}").format(self.entry_type))

        if self.entry_type == "Transfer" and self.from_warehouse == self.to_warehouse:
            frappe.throw(_("From and To Warehouse cannot be the same for a Transfer"))

        if self.entry_type == "Adjustment":
            if self.adjustment_type == "Positive" and not self.to_warehouse:
                frappe.throw(_("To Warehouse is required for Positive Adjustment"))
            elif self.adjustment_type == "Negative" and not self.from_warehouse:
                frappe.throw(_("From Warehouse is required for Negative Adjustment"))

    def validate_items(self):
        """
        Validate items in the Stock Entry
        """
        if not self.get("items") or not len(self.get("items")):
            frappe.throw(_("Stock entry must have at least one item"))

        for item in self.items:
            # Validate basic item data
            if not item.item_code:
                frappe.throw(_("Row {0}: Item Code is required").format(item.idx))

            if not item.quantity or flt(item.quantity) <= 0:
                frappe.throw(
                    _("Row {0}: Quantity must be greater than 0").format(item.idx)
                )

            # Fetch item details if not already set
            if not item.item_name:
                item_doc = frappe.get_doc("Item", item.item_code)
                item.item_name = item_doc.item_name
                item.uom = item_doc.uom

                # Set valuation rate for new items if not set
                if not item.basic_rate and self.entry_type in ["Receipt", "Transfer"]:
                    item.basic_rate = item_doc.valuation_rate

            # Calculate amount
            item.basic_amount = flt(item.quantity) * flt(item.basic_rate)

    def validate_stock_availability(self):
        """
        Validate stock availability for issue and transfer
        """
        # Check if negative stock is allowed
        allow_negative_stock = (
            frappe.db.get_single_value("Inventory Settings", "allow_negative_stock")
            or False
        )

        if not allow_negative_stock and self.entry_type in ["Issue", "Transfer"]:
            for item in self.items:
                bin_qty = get_bin_qty(item.item_code, self.from_warehouse)
                if flt(bin_qty) < flt(item.quantity):
                    frappe.throw(
                        _(
                            "Row {0}: Insufficient stock of item {1} in warehouse {2}. Available quantity: {3}"
                        ).format(item.idx, item.item_code, self.from_warehouse, bin_qty)
                    )

        # For Adjustment with negative quantity, validate stock
        if not allow_negative_stock and self.entry_type == "Adjustment":
            for item in self.items:
                if flt(item.quantity) < 0:
                    bin_qty = get_bin_qty(item.item_code, self.from_warehouse)
                    if flt(bin_qty) < abs(flt(item.quantity)):
                        frappe.throw(
                            _(
                                "Row {0}: Insufficient stock of item {1} in warehouse {2} for adjustment. Available quantity: {3}"
                            ).format(
                                item.idx, item.item_code, self.from_warehouse, bin_qty
                            )
                        )

    def calculate_totals(self):
        """
        Calculate total quantity and amount
        """
        self.total_quantity = sum(flt(item.quantity) for item in self.get("items"))
        self.total_amount = sum(flt(item.basic_amount) for item in self.get("items"))

    def set_status(self):
        """
        Set initial status based on workflow state or docstatus
        """
        if hasattr(self, "workflow_state") and self.workflow_state:
            self.status = self.workflow_state
        else:
            if self.docstatus == 0:
                self.status = "Draft"
            elif self.docstatus == 1:
                self.status = "Submitted"
            elif self.docstatus == 2:
                self.status = "Cancelled"


def get_bin_qty(item_code, warehouse):
    """
    Get quantity from Bin
    """
    bin_data = frappe.db.get_value(
        "Bin",
        {"item_code": item_code, "warehouse": warehouse},
        "actual_qty",
        as_dict=True,
    )

    return flt(bin_data.actual_qty) if bin_data and bin_data.actual_qty else 0
