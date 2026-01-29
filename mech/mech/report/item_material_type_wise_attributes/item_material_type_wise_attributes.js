// Copyright (c) 2026, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.query_reports["Item Material Type Wise Attributes"] = {
	"filters": [
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group"
		},
		{
			"fieldname": "material_type",
			"label": __("Material Type"),
			"fieldtype": "Link",
			"options": "Material Type MW"
		}
	]
};