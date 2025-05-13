import frappe
from frappe.utils import flt, cint, cstr, nowdate, nowtime, get_datetime, add_days
from inventoree.inventoree.stock_ledger import make_stock_ledger_entries
from inventoree.inventoree.stock_ledger import update_bin_from_sle


def on_cancel(doc, method):
    """
    Actions on cancel
    """
    update_stock_ledger(doc, is_cancelled=1)
    update_bin(doc)


def on_change(doc, method):
    """
    Actions on change
    """

    # Dijalankan saat status berubah
    # frappe.msgprint(f"Status changed to {doc.status}")

    if doc.status == "Submitted" and doc.entry_type == "Receipt":
        # Create Stock Ledger Entries
        update_stock_ledger(doc)

        # Update Bin records
        update_bin_records(doc)


def update_stock_ledger(doc, is_cancelled=0):
    """
    Update Stock Ledger Entries
    """
    sl_entries = []

    for item in doc.items:
        # Handle different entry types
        if doc.entry_type == "Receipt":
            # Inward entry to to_warehouse
            sl_entries.append(get_sl_entry(
                doc, item, doc.to_warehouse, flt(item.quantity), is_cancelled))

        elif doc.entry_type == "Issue":
            # Outward entry from from_warehouse
            sl_entries.append(get_sl_entry(
                doc, item, doc.from_warehouse, -1 * flt(item.quantity), is_cancelled))

        elif doc.entry_type == "Transfer":
            # Outward entry from from_warehouse
            sl_entries.append(get_sl_entry(
                doc, item, doc.from_warehouse, -1 * flt(item.quantity), is_cancelled))

            # Inward entry to to_warehouse
            sl_entries.append(get_sl_entry(
                doc, item, doc.to_warehouse, flt(item.quantity), is_cancelled))

        elif doc.entry_type == "Adjustment":
            # Adjustment can be positive or negative
            if flt(item.quantity) > 0:
                sl_entries.append(get_sl_entry(
                    doc, item, doc.to_warehouse, flt(item.quantity), is_cancelled))
            else:
                sl_entries.append(get_sl_entry(
                    doc, item, doc.from_warehouse, flt(item.quantity), is_cancelled))

    # Create Stock Ledger Entries
    if sl_entries:
        make_sl_entries(doc, sl_entries)


def get_sl_entry(doc, item, warehouse, qty, is_cancelled=0):
    """
    Prepare data for Stock Ledger Entry
    """
    # If cancelled, reverse qty
    actual_qty = -1 * qty if is_cancelled else qty

    # Set incoming rate for positive quantity or transfer
    incoming_rate = flt(item.basic_rate) if qty > 0 else 0

    # Create SLE data
    sle = {
        "item_code": item.item_code,
        "item_name": item.item_name,
        "warehouse": warehouse,
        "posting_date": doc.posting_date,
        "posting_time": doc.posting_time,
        "voucher_type": "Stock Entry",
        "voucher_no": doc.name,
        "voucher_detail_no": item.name,
        "incoming_rate": incoming_rate,
        "actual_qty": actual_qty,
        "uom": item.uom,
    }

    return sle


def make_sl_entries(doc, sl_entries):
    """
    Create multiple Stock Ledger Entries
    """
    make_stock_ledger_entries(sl_entries)


def update_bin(doc):
    """
    Update bin qty after Stock Entry submit/cancel
    """

    # Update bins for all affected warehouses and items
    affected_items = {}

    for item in doc.items:
        if doc.entry_type == "Receipt":
            affected_items.setdefault(
                item.item_code, []).append(doc.to_warehouse)

        elif doc.entry_type == "Issue":
            affected_items.setdefault(
                item.item_code, []).append(doc.from_warehouse)

        elif doc.entry_type == "Transfer":
            affected_items.setdefault(
                item.item_code, []).append(doc.from_warehouse)
            affected_items.setdefault(
                item.item_code, []).append(doc.to_warehouse)

        elif doc.entry_type == "Adjustment":
            warehouse = doc.to_warehouse if flt(
                item.quantity) > 0 else doc.from_warehouse
            affected_items.setdefault(item.item_code, []).append(warehouse)

    # Ensure unique warehouses for each item
    for item_code, warehouses in affected_items.items():
        for warehouse in list(set(warehouses)):
            update_bin_from_sle(item_code, warehouse)
