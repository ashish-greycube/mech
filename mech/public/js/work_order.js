frappe.ui.form.on("Work Order", {
    refresh: function(frm){
        if (frm.doc.docstatus == 0){
            frm.set_df_property("custom_cutting_status", "read_only", 1)
        }
        else if (frm.doc.docstatus == 1){
            frm.set_df_property("custom_cutting_status", "read_only", 0)
        }
    },
})