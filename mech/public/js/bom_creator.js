frappe.ui.form.on("BOM Creator", {
    custom_download_operation_excel: function(frm){
        open_url_post(
					"/api/method/mech.api.download_operation_formatted_excel",
					{
                        bom_uploader: frm.doc.custom_bom_uploader_ref,
                        name: frm.doc.name
					}
				);
    }
})