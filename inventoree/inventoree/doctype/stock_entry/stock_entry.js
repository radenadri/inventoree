// Copyright (c) 2025, radenadri and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Entry", {
  refresh: function (frm) {
    // Tampilkan action buttons sesuai state
    if (frm.doc.workflow_state === "In Transit") {
      frm.add_custom_button(__("Update Tracking Info"), function () {
        // Custom dialog untuk update info
      });
    }

    // Tampilkan history perubahan state
    if (frm.doc.docstatus == 1) {
      frm.add_custom_button(__("Show State History"), function () {
        frappe.route_options = { reference_name: frm.doc.name };
        frappe.set_route("List", "Workflow Action");
      });
    }
  },
});

frappe.ui.form.on("Stock Entry Item", {
  item_code: function (frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.item_code) {
      // Ambil valuation_rate dari Item dan set sebagai Basic Rate
      frappe.db.get_value(
        "Item",
        row.item_code,
        "valuation_rate",
        function (r) {
          if (r && r.valuation_rate) {
            frappe.model.set_value(cdt, cdn, "basic_rate", r.valuation_rate);
          }
        }
      );

      // Set quantity menjadi 1
      frappe.model.set_value(cdt, cdn, "quantity", 1);
    }
  },

  quantity: function (frm, cdt, cdn) {
    // Hitung Basic Amount saat Quantity berubah
    calculate_basic_amount(frm, cdt, cdn);
  },

  basic_rate: function (frm, cdt, cdn) {
    // Hitung Basic Amount saat Basic Rate berubah
    calculate_basic_amount(frm, cdt, cdn);
  },
});

function calculate_basic_amount(frm, cdt, cdn) {
  let row = locals[cdt][cdn];

  if (row.quantity && row.basic_rate) {
    let basic_amount = flt(row.quantity) * flt(row.basic_rate);

    // Force update dengan nilai baru
    frappe.model.set_value(cdt, cdn, "basic_amount", basic_amount);
  }
}
