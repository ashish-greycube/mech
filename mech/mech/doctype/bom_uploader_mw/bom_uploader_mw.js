// Copyright (c) 2025, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("BOM Uploader MW", {
	refresh(frm){
		$('.grid-add-row').hide()
		$('.grid-remove-rows').hide()

		//////// Autocomplete Field Type ////////
		// if (frm.doc.dam_code == "DAM0124"){
		// 	frm.fields_dict.test.set_data(["three", "Four"])
		// }
		// else{
		// 	frm.fields_dict.test.set_data(["One", "two"])
		// }
	},
	dam_code(frm){
		if (frm.doc.dam_code){
			frm.call('get_sales_order')
		}
		else{
			frm.set_value('order_no', '')
			frm.set_value('client', '')
			frm.set_value('project', '')
		}
	},
	download_formatted_excel(frm) {
        open_url_post(
					"/api/method/mech.mech.doctype.bom_uploader_mw.bom_uploader_mw.download_formatted_excel",
					{
                        name: frm.doc.name,
					}
				);
	},
});



/////////////////// Multiple Matched Item ///////////////////

// frappe.ui.form.on("BOM Item Details MW", {
// 	choose_item: function (frm, cdt, cdn) {
// 		let row = locals[cdt][cdn]
// 		console.log('choose item------->', row.name)

// 		let dialog = undefined
// 		const dialog_field = []

// 		let matched_items = []
// 		if (row.idx == 1){
// 			matched_items = ["aaa", "bbb", "ccc"]
// 		}
// 		else if (row.idx == 2){
// 			matched_items = ["111", "222", "333"]
// 		}
// 		else{
// 			matched_items = ["@@@", "###", "$$$"]
// 		}

// 		dialog_field.push(
// 			{
// 				fieldtype: "Select",
// 				fieldname: "select_item",
// 				label: __("Matched Items"),
// 				options: matched_items,
// 				read_only: 0,
// 			},
// 		)

// 		 dialog = new frappe.ui.Dialog({
// 			title: __("Select Item"),
// 			fields: dialog_field,
// 			primary_action_label: 'Get Items',
// 			primary_action: function (values) {
// 				console.log(values, "-----values")
// 				dialog.hide();
// 			}
// 		 })
// 		 dialog.show()
// 	}
// })
