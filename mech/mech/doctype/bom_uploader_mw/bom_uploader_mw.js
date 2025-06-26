// Copyright (c) 2025, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("BOM Uploader MW", {
	refresh(frm){
		$('.grid-add-row').hide()
		$('.grid-remove-rows').hide()
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

frappe.ui.form.on("BOM Item Details MW", {
	choose_item: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn]
		console.log('choose item------->', row.name)
		let dialog = undefined
		const dialog_field = []

		if (row.status == "Not Found" || (row.status == "Match" && (!row.matched_item_list || row.matched_item_list == ''))){
			let sub_assembly_item_group = ""
			frappe.db.get_single_value('Mechwell Setting MW', 'default_item_group_for_sub_assembly')
				.then(item_group => {
					console.log(item_group);
					sub_assembly_item_group = item_group
				})

			dialog_field.push(
				{
					fieldtype: "Link",
					fieldname: "select_item",
					label: __("Items"),
					options: "Item",
					read_only: 0,
					get_query: () => {
						return{
							filters: {
								"item_group": ["!=", sub_assembly_item_group],
								"custom_material_type": ["=", row.material_type]
							}
						}
					}
				},
			)
		}

		else if (row.matched_item_list) {
			let str = row.matched_item_list || "";
			let array = str.split(",").map(s => s.trim().replace(/'/g, ''));

			if (array.length === 1 ) {
				frappe.show_alert({
				message:__('Matched Item already Selected'),
				indicator:'green'
				}, 5);
			}

			else if (array.length > 1) {
			dialog_field.push(
				{
					fieldtype: "Link",
					fieldname: "select_item",
					label: __("Items"),
					options: "Item",
					read_only: 0,
					get_query: () => {
						return{
							filters: {
								"name": ["in", array],
							}
						}
					}
				},
			)
		}	
		}
		if (dialog_field.length > 0){
			dialog = new frappe.ui.Dialog({
				title: __("Select Item"),
				fields: dialog_field,
				primary_action_label: 'Get Items',
				primary_action: function (values) {
					console.log(values, "-----values")
					if (values){
						let selected_item = values.select_item;
						frappe.model.set_value(cdt, cdn, 'matched_item', selected_item);
						frappe.model.set_value(cdt, cdn, 'status', 'Match');
						// frm.save()
					}
					dialog.hide();
				}
			})
		dialog.show()
		}
	}
})
