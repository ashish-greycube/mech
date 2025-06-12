# Copyright (c) 2025, GreyCube Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr
from frappe.utils.xlsxutils import (
	build_xlsx_response,
	read_xlsx_file_from_attached_file,
	make_xlsx
)
import re
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from copy import copy as xl_copy
import os
from io import BytesIO
from frappe.desk.utils import provide_binary_file

TABLE_HEADERS = [
			"Row No",
			"Parent FG",
			"BOM Item Code",
			"Sr No",
			"Description",
			"Length",
			"Width",
			"OD",
			"ID",
			"Thickness",
			"Material Type",
			"Qty",
			"GAD/MFG",
		]

class BOMUploaderMW(Document):
	def validate(self):

		if self.import_excel:
			excel_data = self.read_excel()
			self.validate_imported_excel(excel_data)

		self.clear_table_data_if_not_attached_file()
		# self.set_matched_item_in_bom_items()

	###### get connected sales order of item ######
	@frappe.whitelist()
	def get_sales_order(self):
		so_item = frappe.db.get_value('Sales Order Item', {'item_code': self.dam_code}, 'parent')
		if not so_item:
			frappe.throw(_("For Item {0} no Sales Order Found.").format(self.dam_code))

		customer, project = frappe.db.get_value('Sales Order', so_item, ['customer', 'project'])
		self.order_no = so_item
		self.client = customer
		self.project = project

	@frappe.whitelist()
	def read_excel(self):
		file_doc = frappe.get_doc("File", {"file_url": self.import_excel})
		data = read_xlsx_file_from_attached_file(fcontent=file_doc.get_content())

		return data

	###### Excel validation  ######
	def validate_imported_excel(self, excel_data):

		if len(self.bom_item_details_mw) < 1:
			# validate file name
			file_name = frappe.db.get_value('File', { 'file_url': self.import_excel}, 'file_name')
			if file_name and self.name not in file_name:
				frappe.throw(_("Import Excel File name should be starts from {0}").format(self.name))

			# check table exists or not
			if len(excel_data) < 9:
				frappe.throw(_("Please add table data in excel"))

			# print(excel_data, '------------excel_data------------')

			excel_table_data = self.get_excel_table_data(excel_data)
			self.validate_naming_and_sr_no_of_items(excel_table_data)

			alphabetic_items_details, alphanumeric_items_details = self.create_level_1_and_2_item_lists(excel_table_data)
			table_header_col = excel_data[7]

			# print(len(alphabetic_items_details), "============alphabetic_items_details============")
			# print(len(alphanumeric_items_details), "============alphanumeric_items_details============")

			self.validate_excel_columns(table_header_col)
			self.check_in_excel_all_matrial_type_exists(excel_table_data)
			self.validate_mandatory_fields_in_excel(excel_table_data, alphanumeric_items_details)
			# validate_material_type_for_alphanumeric_items_in_excel(alphanumeric_items_details)

			self.fill_bom_item_details_table(excel_table_data, alphabetic_items_details)

	def get_excel_table_data(self, excel_data):
		data_len = len(excel_data)

		table_data = []
		for idx in range(8, data_len):
			row = excel_data[idx]
			if all(v is None for v in row) == False:

				##### remove blank row for data #####
				blank_row = True
				for a in row:
					if cstr(a).strip() != '':
						blank_row = False

				# print(blank_row, '-------------blank_row---------------')
				if blank_row == False:	
					table_data.append({
						"idx": idx + 1, 
						"row_no": row[0],
						"parent_fg": row[1],
						"bom_item_code": row[2],
						"sr_no": row[3],
						"Description": row[4],
						"Length": row[5],
						"Width": row[6],
						"OD": row[7],
						"ID": row[8],
						"Thickness": row[9],
						"material_type": row[10],
						"Qty": row[11],
						"gad_mfg": row[12]
					})
			else:
				pass

		return table_data

	def validate_naming_and_sr_no_of_items(self, excel_table_data):
		naming_errors = []
		alphabets = []
		for item in excel_table_data:
			###### check level 1 item's sr no - must be unique & alphabetic ######

			if item.get("parent_fg") == self.dam_code:
				if item.get("sr_no") and item.get("sr_no").isalpha() == False:
					msg1 = (
						"In Excel Line No - {0}, Sr No should be alphabetic not {1}"
					).format(item.get("idx"), item.get("sr_no"))
					naming_errors.append(msg1)
					# frappe.throw(_("In Excel Line No - {0}, Sr No should be alphabetic not {1}").format(item.get('idx'), item.get('sr_no')))
				if item.get("sr_no") not in alphabets:
					alphabets.append(item.get("sr_no"))
				elif item.get("sr_no") in alphabets:
					msg2 = ("SR No {0} exists multiple time.").format(item.get("sr_no"))
					naming_errors.append(msg2)
					# frappe.throw(_('SR No {0} exists multiple time.').format(item.get('sr_no')))
			else:
				###### check level 2 item's naming format ######

				dam_code = self.dam_code
				pattern = re.compile(rf"^{re.escape(dam_code)}-[A-Z]+$")
				if not pattern.match(item.get("parent_fg")):
					msg3 = (
						"In Excel Line No - {0}, Incorrect Naming format of Parent FG {1}"
					).format(item.get("idx"), item.get("parent_fg"))
					naming_errors.append(msg3)
					# frappe.throw(_("In Excel Line No - {0}, Incorrect Naming format of Parent FG {1}").format(item.get('idx'), item.get('parent_fg')))

		if len(naming_errors) > 0:
			frappe.throw(
				"Please Correct Below Naming Errors: <br> {0}".format(
					",<br>".join((ele if ele != None else "") for ele in naming_errors)
				)
			)

	def create_level_1_and_2_item_lists(self, excel_table_data):
		alphabetic_items = []
		alphanumeric_items = []
		for row in excel_table_data:
			sr_no = row.get("sr_no")
			if sr_no and sr_no.isalpha() == False:
				alphanumeric_items.append(row)
			else:
				alphabetic_items.append(row)

		return alphabetic_items, alphanumeric_items

	def validate_excel_columns(self, excel_column):
		print(excel_column)
		a = excel_column
		b = TABLE_HEADERS
		# print(list(zip(a, b)), '---------zip(a, b)-------')
		is_equal = all(a == b for a, b in zip(a, b))
		if not is_equal:
			frappe.throw(_("In excel row 8 : Table Header Columns Must Be {0}").format(
					TABLE_HEADERS))

	def check_in_excel_all_matrial_type_exists(self, excel_table_data):
		material_type_list = []
		# print(excel_table_data, "-------excel_table_data")
		for row in excel_table_data:
			material_type = row.get("material_type")
			if material_type and material_type not in material_type_list:
				material_type_list.append(material_type)

		# print(material_type_list, '------------material_type_list----------------')
		if len(material_type_list) > 0:
			not_exists_mt = []
			for mt in material_type_list:
				if not frappe.db.exists("Material Type MW", mt):
					not_exists_mt.append(mt)

			if len(not_exists_mt) > 0:
				frappe.throw(_("Following material types are not exists: <br> {0}").format(
						",<br>".join((ele if ele != None else "") for ele in not_exists_mt)))

	def validate_mandatory_fields_in_excel(
		self, excel_table_data, alphanumeric_items_details
	):
		error_list = []
		for row in excel_table_data:
			excel_idx = row.get("idx")
			table_idx = row.get("row_no")

			not_exists_col = []
			if not row.get("row_no"):
				not_exists_col.append("<b>Row No</b>")
			if not row.get("parent_fg"):
				not_exists_col.append("<b>Parent FG</b>")
			if not row.get("sr_no"):
				not_exists_col.append("<b>SR No</b>")
			if not row.get("Description"):
				not_exists_col.append("<b>Description</b>")
			if not row.get("Qty"):
				not_exists_col.append("<b>Qty</b>")
			if not row.get("gad_mfg"):
				not_exists_col.append("<b>GAD/MFG</b>")

			###### validate material type for alphanumeric items ######
			if row in alphanumeric_items_details:
				if not row.get("material_type"):
					not_exists_col.append("<b>Material Type</b>")

				###### check attributes based on material type ######
				# print(row.get("material_type"), "------------row.get")
				if row.get("material_type"):
					mt = frappe.get_doc("Material Type MW", row.get("material_type"))
					if len(mt.attributes) > 0:
						for a in mt.attributes:
							excel_column_title = frappe.db.get_value(
								"Attribute MW", a.attribute, "excel_column_title"
							)
							# print(excel_column_title, '--------row.get(excel_column_title)--------')
							if not row.get(excel_column_title):
								attr = "<b>" + excel_column_title + "</b>"
								not_exists_col.append(attr)

			if len(not_exists_col) > 0:
				if row.get("row_no"):
					msg = (
						"In Excel Line No - " + cstr(excel_idx) + ", Data Row No - " + cstr(table_idx) + " : " + (" and ".join((ele if ele != None else "") for ele in not_exists_col)))
				else:
					msg = ("In Excel Line No - " + cstr(excel_idx) + " : " + (" and ".join((ele if ele != None else "") for ele in not_exists_col )))

				error_list.append(msg)

		if len(error_list) > 0:
			frappe.throw(
				"Please Set Mandatory Field In Following Excel Columns: <br> {0}".format(
					",<br>".join((ele if ele != None else "") for ele in error_list)
				))

	def fill_bom_item_details_table(self, excel_table_data, alphabetic_items_details):
		if len(self.bom_item_details_mw) < 1:
			# print("----------------fill_bom_item_details_table------------------" * 5)
			for data in excel_table_data:
				item = self.append("bom_item_details_mw", {})
				item.row_no = data.get("row_no")
				item.parent_fg = data.get("parent_fg")
				item.bom_item_code = data.get("bom_item_code")
				item.sr_no = data.get("sr_no")
				item.description = data.get("Description")
				item.length = data.get("Length")
				item.width = data.get("Width")
				item.od = data.get("OD")
				item.id = data.get("ID")
				item.thickness = data.get("Thickness")
				item.material_type = data.get("material_type")
				item.qty = data.get("Qty")
				item.gad_mfg = data.get("gad_mfg")

				if data in alphabetic_items_details:
					item.item_level = "Level 1"
				else:
					item.item_level = "Level 2"

				# if item.material_type and item.item_level == "Level 2":
				# 	print(item.material_type, '------------', item.idx, "---------------")
				# 	item.matched_item_list = self.get_matched_item(item)

	def clear_table_data_if_not_attached_file(self):
		if not self.import_excel:
			self.bom_item_details_mw = []

	def set_matched_item_in_bom_items(self):
		if len(self.bom_item_details_mw) > 0:
			for item in self.bom_item_details_mw:
				if item.item_level == "Level 2" and item.material_type:
					field_map = attributes_field_mapping()

					sub_assembly_item_group = frappe.db.get_single_value('Mechwell Setting MW', 'default_item_group_for_sub_assembly')
					sql = "SELECT name FROM `tabItem` WHERE custom_material_type = '{0}' AND item_group !='{1}' ".format(item.material_type, sub_assembly_item_group)
					conditions = []

					attr_doc = frappe.get_doc('Material Type MW', item.material_type)
					for att in attr_doc.attributes:
						att_map = frappe._dict(field_map[att.attribute])

						if att.attribute == 'Sub Assembly Keyword':
							conditions.append(" ( %({})s like concat('%%', {}, '%%') ) ".format(att_map.field_name_in_bom_uploader, att_map.field_name_in_item_dt))
						elif att.match_type == '>=':
							# if len(attr_doc.attributes) == 1:
							conditions.append(" ( {field_name_in_item_dt} = (select min({field_name_in_item_dt}) from tabItem where {field_name_in_item_dt} >= %({field_name_in_bom_uploader})s) ) ".format(**att_map))
							# else:
							# 	conditions.append(" ( {field_name_in_item_dt} = (select min({field_name_in_item_dt}) from tabItem where {field_name_in_item_dt} >= %({field_name_in_bom_uploader})s) OR {field_name_in_item_dt} >=  %({field_name_in_bom_uploader})s ) ".format(**att_map))
						elif att.match_type == '<=':
							# if len(attr_doc.attributes) == 1:
							conditions.append(" ( {field_name_in_item_dt} = (select max({field_name_in_item_dt}) from tabItem where {field_name_in_item_dt} <= %({field_name_in_bom_uploader})s) ) ".format(**att_map))
							# else:
							# 	conditions.append(" ( {field_name_in_item_dt} = (select max({field_name_in_item_dt}) from tabItem where {field_name_in_item_dt} <= %({field_name_in_bom_uploader})s) OR {field_name_in_item_dt} <=  %({field_name_in_bom_uploader})s ) ".format(**att_map))
						elif att.match_type == '==':
							conditions.append(" ( {} = %({})s ) ".format(att_map.field_name_in_item_dt, att_map.field_name_in_bom_uploader))

					if conditions:
						print(conditions, "==========conditions====================")
						sql = sql + " AND " + " AND ".join(conditions) + ' LIMIT 10'

					matched_items = frappe.db.sql(sql, item.as_dict(), pluck='name', debug=1)
					item.matched_item_list = ','.join(matched_items)
					print(item.matched_item_list, '-------------------print(item.matched_item_list)----------------------')

def attributes_field_mapping():
	attribute_mw = frappe.db.get_all('Attribute MW', fields=['name', 'field_name_in_item_dt', 'field_name_in_bom_uploader'])
	field_map = {}
	for d in attribute_mw:
		field_map[d.name] = d     
	# print(field_map)

	return field_map


######### create excel - no formatting #########
# @frappe.whitelist()
# def download_formatted_excel(name=None):
# 	doc = frappe.get_doc("BOM Uploader MW", name) if name else None
# data = [
# 	["", "", "Dam code", doc.dam_code],
# 	["", "", "Order No", doc.order_no],
# 	["", "", "Client", doc.client],
# 	["", "", "Project", doc.project],
# 	["", "", "Wt(kg)", doc.total_weight],
# 	["Instruction : Please input data from row no 9. Donot put blank rows while data input"],
# 	[],
# 	TABLE_HEADERS,
# ]

# 	file_name = doc.name
# 	return build_xlsx_response(data, file_name)

@frappe.whitelist()
def download_formatted_excel(name=None):
	doc = frappe.get_doc("BOM Uploader MW", name) if name else None
	print("Downloading formatted Excel file...")

	workbook = Workbook()
	sheet = workbook.active

	rows_data = [
		["", "", "Dam code", doc.dam_code],
		["", "", "Order No", doc.order_no],
		["", "", "Client", doc.client],
		["", "", "Project", doc.project],
		["", "", "Wt(kg)", doc.total_weight],
		["Instruction : Please input data from row no 9. Donot put blank rows while data input"],
		[],
		TABLE_HEADERS,
	]

	for row in rows_data:
		sheet.append(row)

	sheet.column_dimensions['A'].width = 10
	sheet.column_dimensions['B'].width = 12
	sheet.column_dimensions['C'].width = 15
	sheet.column_dimensions['D'].width = 10
	sheet.column_dimensions['E'].width = 20
	sheet.column_dimensions['F'].width = 10
	sheet.column_dimensions['G'].width = 10
	sheet.column_dimensions['H'].width = 10
	sheet.column_dimensions['I'].width = 10
	sheet.column_dimensions['J'].width = 10
	sheet.column_dimensions['K'].width = 20
	sheet.column_dimensions['L'].width = 10
	sheet.column_dimensions['M'].width = 10

	bg_fill = PatternFill(fill_type='solid', start_color='FF474C', end_color='FF474C')

	cells_to_style = ['A8', 'B8', 'D8','E8', 'K8', 'L8', 'M8']
	for cell_coord in cells_to_style:
		cell = sheet[cell_coord]
		cell.fill = bg_fill

	xlsx_file = BytesIO()
	workbook.save(xlsx_file)

	provide_binary_file(doc.name, 'xlsx', xlsx_file.getvalue())

def get_item_list_not_in_sub_assembly_group_and_same_material_type(material_type):
	sub_assembly_item_group = frappe.db.get_single_value('Mechwell Setting MW', 'default_item_group_for_sub_assembly')
	if not sub_assembly_item_group:
		frappe.throw(_("Please set Default Item Group for Sub Assembly In Mechwell Settings Doctype."))

	item_list = frappe.db.sql_list("""select name from `tabItem`
					where item_group !='{0}' and custom_material_type='{1}'""".format(sub_assembly_item_group, material_type))
	

	return item_list

def get_matched_item_based_on_material_attributes(material_type, item_list):
	matched_items = []

	return matched_items
