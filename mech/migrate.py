import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_migrate():
	create_custom_fields_in_core_doctype()
	create_material_attributes()

def create_custom_fields_in_core_doctype():
	custom_fields = {
	   "Item" : [
			{
				"fieldname": "custom_wmf",
				"fieldtype": "Float",
				"label": "Weight Multiplication Factor(WMF)",
				"insert_after": "stock_uom",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_raw_material_attributes",
				"fieldtype": "Tab Break",
				"label": "Raw Material Attributes",
				"insert_after": "total_projected_qty",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_material_type",
				"fieldtype": "Link",
				"label": "Material Type",
				"insert_after": "custom_raw_material_attributes",
				"options":"Material Type MW",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_length",
				"fieldtype": "Float",
				"label": "Length",
				"insert_after": "custom_material_type",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_width",
				"fieldtype": "Float",
				"label": "Width",
				"insert_after": "custom_length",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_sub_assembly_keyword",
				"fieldtype": "Data",
				"label": "Sub Assembly Keyword",
				"insert_after": "custom_width",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_column_break_1",
				"fieldtype": "Column Break",
				"insert_after": "custom_sub_assembly_keyword",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_outer_diameter",
				"fieldtype": "Float",
				"label": "Outer Diameter (OD)",
				"insert_after": "custom_column_break_1",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_inner_diameter",
				"fieldtype": "Float",
				"label": "Inner Diameter (ID)",
				"insert_after": "custom_outer_diameter",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_thickness",
				"fieldtype": "Float",
				"label": "Thickness",
				"insert_after": "custom_inner_diameter",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
		],

		"Item Group":[
			{
				"fieldname": "custom_section_break_1",
				"fieldtype": "Section Break",
				"insert_after": "column_break_5",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_density",
				"fieldtype": "Float",
				"label": "Density",
				"insert_after": "custom_section_break_1",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_column_break_2",
				"fieldtype": "Column Break",
				"insert_after": "custom_density",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_formula_help",
				"fieldtype": "HTML",
				"label": "Help",
				"insert_after": "custom_column_break_2",
				"is_custom_field": 1,
				"is_system_generated": 0,
				"options": "<h4> Weight Formula Symbols & Instructions</h4><h5>Use the following symbols in your weight formulas:</h5><table border=1 class='text-center'><tr><th width=50%>Symbol</th><th width=50%>Meaning</th></tr><tr><td>L</td><td>Length</td></tr><tr><td>W</td><td>Width</td></tr><tr><td>T</td><td>Thickness</td></tr><tr><td>D</td><td>Density</td></tr><tr><td>OD</td><td>Outer Diameter</td></tr><tr><td>ID</td><td>Inner Diameter</td></tr><tr><td>WPM</td><td>Weight Multiplication Factor</td></tr><tr><td>PPW</td><td>Weight Multiplication Factor</td></tr><tr><td>TP</td><td>Quantity</td></tr><tr><td>π</td><td>Pi (3.14)</td></tr></table><br><h4>Example Formulas</h4><ul><li><strong>Basic Formula:</strong><code> ((L * W * T * D) / 100) * TP</code></li><p>Note: Please Enter Flat Formula</p><li><strong>When Total Length (TL) is used:</strong><code> TL = L * TP</code><br><strong>Enter Flat Formula: </strong><code>WPM * (L * TP)</code></li></ul>"
			},
			{
				"fieldname": "custom_section_break_2",
				"fieldtype": "Section Break",
				"label": "Weight Formula",
				"insert_after": "custom_density",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_raw_material_weight_formula",
				"fieldtype": "Code",
				"label": "Raw Material Weight Formula",
				"insert_after": "custom_section_break_2",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_column_break_1",
				"fieldtype": "Column Break",
				"insert_after": "custom_raw_material_weight_formula",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_is_od_formula_exists",
				"fieldtype": "Check",
				"label": "Is OD Based Weight Formula Exists?",
				"description": "Check this if you want to use OD Based Weight Formula",
				"insert_after": "custom_column_break_1",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_od_based_weight_formula",
				"fieldtype": "Code",
				"label": "OD Based Weight Formula",
				"insert_after": "custom_is_od_formula_exists",
				"depends_on": "eval:doc.custom_is_od_formula_exists",
				"mandatory_depends_on": "eval:doc.custom_is_od_formula_exists",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
		],

		"BOM Creator":[
			{
				"fieldname": "custom_section_break_1",
				"fieldtype": "Section Break",
				"label": "BOM Uploader Details",
				"insert_after": "company",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_bom_uploader_ref",
				"fieldtype": "Link",
				"label": "BOM Uploader Reference",
				"insert_after": "custom_section_break_1",
				"options": "BOM Uploader MW",
				"read_only": 1,
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_section_break_2",
				"fieldtype": "Section Break",
				"label": "Operations",
				"insert_after": "custom_bom_uploader_ref",
				"depends_on" : "eval:doc.custom_bom_uploader_ref",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_download_operation_excel",
				"fieldtype": "Button",
				"label": "Download Operation Excel",
				"insert_after": "custom_section_break_2",
				"is_custom_field": 1,
				"is_system_generated": 0,
			},
			{
				"fieldname": "custom_attach_operation_data",
				"fieldtype": "Attach",
				"label": "Import Operation Data",
				"insert_after": "download_operation_excel",
				"is_custom_field": 1,
				"is_system_generated": 0,
			}
		],

		"BOM Creator Item": [
			{
				"fieldname": "custom_sr_no",
				"fieldtype": "Data",
				"label": "SR No",
				"insert_after": "parent_row_no",
				"read_only": 1,
				"is_custom_field": 1,
				"is_system_generated": 0,
			}
		]

	}

	print("Adding Landed Cost custom field in Item.....")
	for dt, fields in custom_fields.items():
		print("*******\n %s: " % dt, [d.get("fieldname") for d in fields])
	create_custom_fields(custom_fields)


def create_material_attributes():
	attributes = [
		{ "name": "Sub Assembly Length", "excel_column_title" : "Length", "field_name_in_item_dt" : "custom_length", "field_name_in_bom_uploader": "length"},
		{ "name": "Sub Assembly Width", "excel_column_title" : "Width", "field_name_in_item_dt" : "custom_width", "field_name_in_bom_uploader": "width"},
		{ "name": "Thickness", "excel_column_title" : "Thickness", "field_name_in_item_dt" : "custom_thickness", "field_name_in_bom_uploader": "thickness"},
		{ "name": "Outer Diameter (OD)", "excel_column_title" : "OD", "field_name_in_item_dt" : "custom_outer_diameter", "field_name_in_bom_uploader": "od"},
		{ "name": "Inner Diameter (ID)", "excel_column_title" : "ID", "field_name_in_item_dt" : "custom_inner_diameter", "field_name_in_bom_uploader": "id"},
		{ "name": "Sub Assembly Keyword", "excel_column_title" : "Description", "field_name_in_item_dt" : "custom_sub_assembly_keyword", "field_name_in_bom_uploader": "description"},
	]

	for att in attributes:
		if not frappe.db.exists("Attribute MW", att.get('name')):
			new_doc = frappe.new_doc("Attribute MW")
			new_doc.attribute = att.get("name")
			new_doc.excel_column_title = att.get("excel_column_title")
			new_doc.field_name_in_item_dt = att.get("field_name_in_item_dt")
			new_doc.field_name_in_bom_uploader = att.get("field_name_in_bom_uploader")

			new_doc.save(ignore_permissions=True)
		else:
			pass