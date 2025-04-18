frappe.ui.form.on('Purchase Order Item',{

    custom_offered_rate(frm,cdt,cdn){
        updated_discount_amount(frm,cdt,cdn)
        update_item_rate(frm, cdt, cdn)
    },
    custom_discount_percent(frm,cdt,cdn){
        updated_discount_amount(frm,cdt,cdn)
        update_item_rate(frm, cdt, cdn)
    },
    custom_mw_discount_amount(frm,cdt,cdn){
        update_item_rate(frm, cdt, cdn)
    }
})
function updated_discount_amount(frm,cdt,cdn){
    let row = locals[cdt][cdn]
    if(row.custom_offered_rate && row.custom_discount_percent) {
        if(row.custom_discount_percent <= 100){
            let discount_amount = (row.custom_offered_rate / 100) * row.custom_discount_percent
            frappe.model.set_value(row.doctype, row.name, 'custom_mw_discount_amount', discount_amount)
            console.log(row.custom_mw_discount_amount)
        }
        else{
            frappe.throw("Discount Percent cannot be grater then 100..!");
            
        }
       
    }
    else{
        frappe.model.set_value(row.doctype, row.name, 'custom_mw_discount_amount', 0)
    }
}

function update_item_rate(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.custom_offered_rate && row.custom_mw_discount_amount){
        let rate = row.custom_offered_rate - row.custom_mw_discount_amount
        frappe.model.set_value(row.doctype, row.name, 'rate', rate)
    }
    else if (row.custom_offered_rate){
        frappe.model.set_value(row.doctype, row.name, 'rate', row.custom_offered_rate)
    }
    else{
        frappe.model.set_value(row.doctype, row.name, 'rate', 0)
    }
}