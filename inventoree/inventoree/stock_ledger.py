from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, now, get_datetime
import json


def make_stock_ledger_entries(sl_entries, allow_negative_stock=False):
    """
    Create Stock Ledger Entries for stock movements
    Args:
        sl_entries: List of dictionaries containing SLE data
        allow_negative_stock: Whether to allow negative stock or not
    """
    for entry in sl_entries:
        sle = frappe.new_doc("Stock Ledger Entry")

        # Set fields from entry dictionary
        for field, value in entry.items():
            if field != "name" and hasattr(sle, field):
                sle.set(field, value)

        # Calculate qty_after_transaction
        previous_sle = get_previous_sle(
            sle.item_code, sle.warehouse, sle.posting_date, sle.posting_time)

        qty_after_transaction = flt(previous_sle.get(
            'qty_after_transaction', 0)) + flt(sle.actual_qty)

        # Check for negative stock
        if not allow_negative_stock and qty_after_transaction < 0:
            frappe.throw(_("Negative stock error: {0} qty after transaction for item {1} in warehouse {2}")
                         .format(qty_after_transaction, sle.item_code, sle.warehouse))

        # Set qty_after_transaction and stock values
        sle.qty_after_transaction = qty_after_transaction

        # Calculate stock value
        if sle.actual_qty > 0:
            # For incoming stock, use incoming rate
            stock_value_difference = flt(
                sle.actual_qty) * flt(sle.incoming_rate)
        else:
            # For outgoing stock, use valuation rate
            valuation_rate = previous_sle.get('valuation_rate', 0)
            if not valuation_rate:
                valuation_rate = get_item_valuation_rate(sle.item_code)

            stock_value_difference = flt(sle.actual_qty) * flt(valuation_rate)

        # Calculate current stock value
        stock_value = flt(previous_sle.get('stock_value', 0)
                          ) + flt(stock_value_difference)

        # Set calculated values
        sle.stock_value_difference = stock_value_difference
        sle.stock_value = stock_value

        # Calculate new valuation rate
        if qty_after_transaction > 0:
            sle.valuation_rate = stock_value / qty_after_transaction
        else:
            sle.valuation_rate = previous_sle.get('valuation_rate', 0)

        # Set docstatus directly to submitted
        sle.docstatus = 1

        # Insert the SLE
        sle.flags.ignore_permissions = 1
        sle.submit()

        # Debug log
        frappe.msgprint(_("Stock Ledger Entry created for {0} in {1}")
                        .format(sle.item_code, sle.warehouse), alert=True, indicator='green')


def get_previous_sle(item_code, warehouse, posting_date, posting_time):
    """
    Get the last SLE for an item in a warehouse before the specified time
    """
    posting_datetime = get_datetime(posting_date + " " + posting_time)

    entries = frappe.db.sql("""
        SELECT 
            name, qty_after_transaction, valuation_rate, stock_value
        FROM 
            `tabStock Ledger Entry`
        WHERE 
            item_code = %s 
            AND warehouse = %s
            AND TIMESTAMP(posting_date, posting_time) <= %s
        ORDER BY 
            TIMESTAMP(posting_date, posting_time) DESC, 
            creation DESC
        LIMIT 1
    """, (item_code, warehouse, posting_datetime), as_dict=1)

    return entries[0] if entries else {}


def update_bin_from_sle(item_code, warehouse):
    """
    Update Bin based on Stock Ledger Entry
    """
    # Get or create Bin
    bin_doc = get_or_create_bin(item_code, warehouse)

    # Get latest actual_qty from SLE
    actual_qty = get_actual_qty_from_sle(item_code, warehouse)

    # Get other reserved quantities
    # These values would usually come from other documents (PO, SO, etc.)
    # Simplified version here
    ordered_qty = get_ordered_qty(item_code, warehouse)
    reserved_qty = get_reserved_qty(item_code, warehouse)

    # Calculate projected_qty
    projected_qty = (
        flt(actual_qty) +
        flt(ordered_qty) -
        flt(reserved_qty)
    )

    # Update the Bin
    frappe.db.set_value('Bin', bin_doc.name, {
        'actual_qty': actual_qty,
        'projected_qty': projected_qty,
        'ordered_qty': ordered_qty,
        'reserved_qty': reserved_qty
    }, update_modified=False)

    # Update item valuation rate if needed
    update_item_valuation_rate(item_code)


def get_or_create_bin(item_code, warehouse):
    """
    Get existing Bin or create a new one
    """
    bin_name = warehouse + "-" + item_code

    if not frappe.db.exists("Bin", bin_name):
        bin_doc = frappe.new_doc("Bin")
        bin_doc.item_code = item_code
        bin_doc.warehouse = warehouse
        bin_doc.actual_qty = 0
        bin_doc.ordered_qty = 0
        bin_doc.reserved_qty = 0
        bin_doc.indented_qty = 0
        bin_doc.planned_qty = 0
        bin_doc.projected_qty = 0
        bin_doc.stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
        bin_doc.flags.ignore_permissions = 1
        bin_doc.insert()
    else:
        bin_doc = frappe.get_doc("Bin", bin_name)

    return bin_doc


def get_actual_qty_from_sle(item_code, warehouse):
    """
    Get actual quantity from latest Stock Ledger Entry
    """
    latest_sle = frappe.db.sql("""
        SELECT qty_after_transaction
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s
            AND warehouse = %s
        ORDER BY posting_date DESC, posting_time DESC, creation DESC
        LIMIT 1
    """, (item_code, warehouse), as_dict=1)

    return flt(latest_sle[0].qty_after_transaction) if latest_sle else 0


def get_ordered_qty(item_code, warehouse):
    """
    Get ordered but not received quantity
    This would usually come from Purchase Orders
    """
    # Simplified version - in a real implementation, this would query Purchase Order Item
    return 0


def get_reserved_qty(item_code, warehouse):
    """
    Get reserved quantity
    This would usually come from Sales Orders
    """
    # Simplified version - in a real implementation, this would query Sales Order Item
    return 0


def update_item_valuation_rate(item_code):
    """
    Update Item valuation rate based on average of all stock
    """
    total_qty = 0
    total_value = 0

    # Get all bins for the item
    bins = frappe.get_all("Bin",
                          filters={"item_code": item_code,
                                   "actual_qty": [">", 0]},
                          fields=["warehouse", "actual_qty"]
                          )

    for bin_data in bins:
        # Get latest valuation rate from SLE
        latest_sle = frappe.db.sql("""
            SELECT valuation_rate, qty_after_transaction
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s
                AND warehouse = %s
                AND qty_after_transaction > 0
            ORDER BY posting_date DESC, posting_time DESC, creation DESC
            LIMIT 1
        """, (item_code, bin_data.warehouse), as_dict=1)

        if latest_sle:
            qty = flt(bin_data.actual_qty)
            rate = flt(latest_sle[0].valuation_rate)
            total_qty += qty
            total_value += qty * rate

    # Calculate and update new valuation rate
    if total_qty > 0:
        new_valuation_rate = total_value / total_qty

        # Update Item with new valuation rate
        frappe.db.set_value("Item", item_code,
                            "valuation_rate", new_valuation_rate)


def get_item_valuation_rate(item_code):
    """
    Get valuation rate from Item
    """
    return flt(frappe.db.get_value("Item", item_code, "valuation_rate"))


@frappe.whitelist()
def get_stock_balance_for_multiple_items(items, warehouse=None):
    """
    Get stock balance for multiple items
    Args:
        items: List of item codes
        warehouse: Optional warehouse filter
    """
    if isinstance(items, str):
        items = json.loads(items)

    filters = {"item_code": ["in", items]}

    if warehouse:
        filters["warehouse"] = warehouse

    bin_data = frappe.get_all(
        "Bin",
        filters=filters,
        fields=["item_code", "warehouse", "actual_qty", "projected_qty"],
    )

    # Format result as dictionary keyed by item_code
    result = {}
    for row in bin_data:
        if row.item_code not in result:
            result[row.item_code] = []
        result[row.item_code].append({
            "warehouse": row.warehouse,
            "actual_qty": row.actual_qty,
            "projected_qty": row.projected_qty
        })

    return result
