import frappe
from frappe import _
from frappe.utils import get_datetime


def get_item_prefix(doc):
    """
    Returns prefix based on Item Group:
    RM-*: Raw Materials (Bahan Baku)
    FG-*: Finished Goods (Barang Jadi)
    PKG-*: Packaging (Material Pengemas)
    SP-*: Spare Parts (Suku Cadang)
    """
    # Get the item group
    item_group = doc.item_group

    # Set default prefix
    prefix = "ITEM-"

    # Check item group and assign appropriate prefix
    if frappe.db.exists("Item Group", {"name": item_group, "item_group_name": "Raw Materials"}) or frappe.db.exists("Item Group", {"name": item_group, "parent_item_group": "Raw Materials"}):
        prefix = "RM-"
    elif frappe.db.exists("Item Group", {"name": item_group, "item_group_name": "Finished Goods"}) or frappe.db.exists("Item Group", {"name": item_group, "parent_item_group": "Finished Goods"}):
        prefix = "FG-"
    elif frappe.db.exists("Item Group", {"name": item_group, "item_group_name": "Packaging"}) or frappe.db.exists("Item Group", {"name": item_group, "parent_item_group": "Packaging"}):
        prefix = "PKG-"
    elif frappe.db.exists("Item Group", {"name": item_group, "item_group_name": "Spare Parts"}) or frappe.db.exists("Item Group", {"name": item_group, "parent_item_group": "Spare Parts"}):
        prefix = "SP-"

    return prefix


def get_stock_entry_prefix(doc):
    """
    Returns prefix based on Stock Entry Type:
    IS/YYYY/MM/DD/-*: Issue (Pengeluaran)
    RE/YYYY/MM/DD/-*: Receipt (Penerimaan)
    TR/YYYY/MM/DD/-*: Transfer (Transfer Antar Gudang)
    ADJ/YYYY/MM/DD/-*: Adjustment (Pengajuan Koreksi Stok)
    """

    # Get the stock entry type
    entry_type = doc.entry_type

    # Set default prefix
    prefix = "SE"

    # Check stock entry type and assign appropriate prefix
    if entry_type == "Issue":
        prefix = "IS"
    elif entry_type == "Receipt":
        prefix = "RE"
    elif entry_type == "Transfer":
        prefix = "TR"
    elif entry_type == "Adjustment":
        prefix = "ADJ"

    # Append date
    if isinstance(doc.posting_date, str):
        posting_date = get_datetime(doc.posting_date).date()
    else:
        posting_date = doc.posting_date

    prefix += f"/{posting_date.strftime('%Y/%m/%d')}/"

    return prefix


def autoname_item(doc, method):
    """
    Custom naming function for Items.
    Format: [PREFIX]-XXXXX
    Where PREFIX is determined by the item group
    """
    # Get prefix based on item group
    prefix = get_item_prefix(doc)

    # If item_code is already set by user and has proper prefix, use it
    if doc.item_code and doc.item_code.startswith(prefix):
        doc.name = doc.item_code
        return

    # Get the current series number
    current = frappe.db.sql("""
        SELECT MAX(CAST(SUBSTRING_INDEX(name, '-', -1) AS UNSIGNED)) 
        FROM `tabItem` 
        WHERE name LIKE %s
    """, (prefix + '%',))

    # Extract the number
    current_number = current[0][0] if current and current[0][0] else 0

    # Create the new name with incremented number
    next_number = current_number + 1
    doc.name = f"{prefix}{next_number:05d}"

    # Also set the item_code field
    doc.item_code = doc.name


def autoname_stock_entry(doc, method):
    """
    Custom naming function for Stock Entries.
    Format: [PREFIX]-XXXXX
    Where PREFIX is determined by the stock entry type
    """
    # Get prefix based on stock entry type
    prefix = get_stock_entry_prefix(doc)
    # If name is already set by user and has proper prefix, use it
    if doc.name and doc.name.startswith(prefix):
        return
    # Get the current series number
    current = frappe.db.sql("""
        SELECT MAX(CAST(SUBSTRING_INDEX(name, '-', -1) AS UNSIGNED))
        FROM `tabStock Entry`
        WHERE name LIKE %s
    """, (prefix + '%',))

    # Extract the number
    current_number = current[0][0] if current and current[0][0] else 0

    # Create the new name with incremented number
    next_number = current_number + 1
    doc.name = f"{prefix}{next_number:05d}"
