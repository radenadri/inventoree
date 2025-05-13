from __future__ import unicode_literals
import frappe
from frappe import _


def after_install():
    create_default_uom()
    create_default_item_groups()
    create_default_warehouses()
    create_default_settings()


def create_default_uom():
    """Create default UOMs"""
    uoms = [
        {"uom_name": "Nos", "must_be_whole_number": 1, "conversion_factor": 1.0},
        {"uom_name": "Kg", "must_be_whole_number": 0, "conversion_factor": 1.0},
        {"uom_name": "Gram", "must_be_whole_number": 0, "conversion_factor": 0.001},
        {"uom_name": "Liter", "must_be_whole_number": 0, "conversion_factor": 1.0},
        {"uom_name": "Ml", "must_be_whole_number": 0, "conversion_factor": 0.001},
        {"uom_name": "Box", "must_be_whole_number": 1, "conversion_factor": 1.0}
    ]

    for uom in uoms:
        if not frappe.db.exists("UOM", uom["uom_name"]):
            doc = frappe.new_doc("UOM")
            doc.update(uom)
            doc.insert(ignore_permissions=True)


def create_default_item_groups():
    """Create default Item Groups"""
    # Create root item group
    if not frappe.db.exists("Item Group", "All Item Groups"):
        doc = frappe.new_doc("Item Group")
        doc.item_group_name = "All Item Groups"
        doc.is_group = 1
        doc.insert(ignore_permissions=True)


def create_default_warehouses():
    """Create default Warehouses"""
    # Create root warehouse
    if not frappe.db.exists("Warehouse", "All Warehouses"):
        doc = frappe.new_doc("Warehouse")
        doc.warehouse_name = "All Warehouses"
        doc.is_group = 1
        doc.insert(ignore_permissions=True)


def create_default_settings():
    """Create default inventory settings"""
    # This would depend on your settings DocType structure
    pass
