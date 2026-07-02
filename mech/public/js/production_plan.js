frappe.ui.form.on("Production Plan", {
    refresh: function (frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(
                __("Create Subcontract Request"),
                () => {
                    create_subcontract_request(frm)
                },
                __("Create")
            )
        }
    },
})

function create_subcontract_request(frm) {
    let dialog = undefined
    const table_fields = [
        {
            fieldname: "production_item",
            label: __("Sub Assembly Item Code"),
            fieldtype: "Link",
            options: "Item",
            in_list_view: 1,
            columns: 4
        },
        {
            fieldname: "bom_no",
            label: __("BOM No"),
            fieldtype: "Link",
            options: "BOM",
            in_list_view: 1,
            columns: 4
        },
        {
            fieldname: "production_item_ref",
            label: "production_item_ref",
            fieldtype: "Data",
            in_list_view: 0,
            hidden: 1
        }
    ]

    const dialog_field = [
        {
            label: __("Sub Assembly Items"),
            fieldname: 'assembly_items',
            fieldtype: 'Table',
            cannot_add_rows: true,
            cannot_delete_rows: true,
            in_place_edit: false,
            data: [],
            get_data: () => {
                return [];
            },
            fields: table_fields,
            description: "In Item Master, the 'Subcontracted Item' option must be enabled to create a Subcontract Material Request."
        }
    ]

    dialog = new frappe.ui.Dialog({
        title: __("Select Items to Create Subcontracting Material Request"),
        fields: dialog_field,
        primary_action_label: __('Create'),
        primary_action: function (values) {
            // console.log(values, "====values=====")
            let selected_items = dialog.fields_dict.assembly_items.grid.get_selected_children()
            if (selected_items.length < 1) {
                frappe.msgprint(__("Please select Atleast one item to create subcontracting material request."))
            }
            else { 
                dialog.hide();
                // console.log(selected_items, "=====data=========")
                frappe.call({
                    method: "mech.api.create_subcontracting_material_request_for_production_plan",
                    args: {
                        "assembly_items": selected_items,
                        "production_plan": frm.doc.name
                    }
                })
            }

        }

    });

    dialog.fields_dict.assembly_items.df.data = [];

    if (frm.doc.sub_assembly_items && frm.doc.sub_assembly_items.length > 0) {
        // frm.doc.sub_assembly_items.forEach(row => {
        frappe.call({
            method: "mech.api.get_valid_subcontract_item_for_mr",
            args: {
                "production_plan": frm.doc.name,
                "sub_assembly_items": frm.doc.sub_assembly_items
            },
            callback: (r) => {
                // console.log(r, "============r===========")
                if (r.message && r.message.length > 0) {
                    r.message.forEach(row => {
                        dialog.fields_dict.assembly_items.df.data.push({
                            'production_item': row.production_item,
                            'bom_no': row.bom_no,
                            'assembly_item_ref': row.name,
                            'schedule_date': row.schedule_date,
                            'qty': row.qty,
                            'uom': row.uom,
                            'stock_uom': row.stock_uom,
                            'actual_qty': row.actual_qty
                        });
                    })
                    dialog.fields_dict.assembly_items.grid.refresh();
                    dialog.show();
                }
                else {
                    frappe.msgprint(__("No valid subcontracted items found. <br> Note: In Item Master, the 'Subcontracted Item' option must be enabled to create a Subcontract Material Request."));
                }
            }
        })
    }

}