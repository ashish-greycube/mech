# Copyright (c) 2025, GreyCube Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, get_link_to_form
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
		self.set_matched_item_in_bom_items()
		self.check_if_item_is_bought_out()
		self.calculate_raw_material_weight()

	def before_submit(self):
		self.check_if_all_matched_items_found()
		self.make_sub_assembly_items()
	
	def on_submit(self):
		self.make_bom_creator()
	
	def on_cancel(self):
		self.delete_all_sub_assembly_items()


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

			alphabetic_items_details, alphanumeric_items_details = self.create_level_1_and_2_item_lists(excel_table_data)
			table_header_col = excel_data[7]

			# print(len(alphabetic_items_details), "============alphabetic_items_details============")
			# print(len(alphanumeric_items_details), "============alphanumeric_items_details============")

			self.validate_excel_columns(table_header_col)
			self.check_in_excel_all_matrial_type_exists(excel_table_data)
			self.validate_mandatory_fields_in_excel(excel_table_data, alphanumeric_items_details)
			self.validate_naming_and_sr_no_of_items(excel_table_data)
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
						# "bom_item_code": row[2],
						"sr_no": row[2],
						"Description": row[3],
						"Length": row[4],
						"Width": row[5],
						"OD": row[6],
						"ID": row[7],
						"Thickness": row[8],
						"material_type": row[9],
						"Qty": row[10],
						"gad_mfg": row[11]
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
				if item.get("sr_no") and item.get("sr_no") not in alphabets:
					alphabets.append(item.get("sr_no"))
				elif item.get("sr_no") in alphabets:
					msg2 = ("SR No {0} exists multiple time.").format(item.get("sr_no"))
					naming_errors.append(msg2)
					# frappe.throw(_('SR No {0} exists multiple time.').format(item.get('sr_no')))
			else:
				###### check level 2 item's naming format ######

				dam_code = self.dam_code
				pattern = re.compile(rf"^{re.escape(dam_code)}-[A-Z]+$")
				if not pattern.match(item.get("parent_fg")) and item.get("parent_fg"):
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
		# print(excel_column)
		a = excel_column
		b = TABLE_HEADERS
		# print(list(zip(a, b)), '---------zip(a, b)-------')
		is_equal = all(a == b for a, b in zip(a, b))
		if not is_equal:
			frappe.throw(_("In excel row 8 : Table Header Columns Must Be {0}").format(
					TABLE_HEADERS))
	
	#################### ToDo #############################		
	def validate_parent_fg(self, alphabetic_items, alphanumeric_items):
		parent_gf_list = []
		for alpha in alphabetic_items:
			item_name = alpha.get("parent_fg") + "-" + alpha.get("sr_no")
			if item_name not in parent_gf_list:
				parent_gf_list.append(parent_gf_list)

		print(parent_gf_list, "==========parent_gf_list=================")

		error_data = []
		if len(parent_gf_list) > 0:
			for row in alphanumeric_items:
				if row.get("parent_fg") not in parent_gf_list:
					if row.get("parent_fg") not in error_data:
						error_data.append(row.get("parent_fg"))
		
		if len(error_data) > 0:
			frappe.throw(_("Following Parent FGs are not exists: <br> {0}").format(",<br>".join((ele if ele != None else "") for ele in error_data)))


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
				# item.bom_item_code = data.get("bom_item_code")
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
			count = 0
			for item in self.bom_item_details_mw:
				if item.item_level == "Level 2" and item.material_type and not item.matched_item:
					field_map = attributes_field_mapping()

					sub_assembly_item_group = frappe.db.get_single_value('Mechwell Setting MW', 'default_item_group_for_sub_assembly')
					sql = "SELECT name FROM `tabItem` WHERE custom_material_type = '{0}' AND item_group !='{1}' ".format(item.material_type, sub_assembly_item_group)
					conditions = []
					near_by_value = {}

					attr_doc = frappe.get_doc('Material Type MW', item.material_type)

					if len(attr_doc.attributes) > 0:
						
						for att in attr_doc.attributes:
							att_map = frappe._dict(field_map[att.attribute])
							# print(att_map, "==============att_map==========")

							if att.attribute == 'Sub Assembly Keyword':
								conditions.append(" ( %({})s like concat('%%', {}, '%%') ) ".format(att_map.field_name_in_bom_uploader, att_map.field_name_in_item_dt))
							elif att.match_type == '>=':
								conditions.append(" {field_name_in_item_dt} >=  %({field_name_in_bom_uploader})s ".format(**att_map))
								max_value = frappe.db.sql_list(
									"SELECT min({field_name_in_item_dt}) FROM `tabItem` WHERE custom_material_type = '{0}' AND item_group !='{1}' AND {field_name_in_item_dt} >= %({field_name_in_bom_uploader})s".format(item.material_type, sub_assembly_item_group, **att_map),
									item.as_dict()
								)
								# print(max_value, "========================max_value============================")
								if max_value and max_value[0]:
									near_by_value[att_map.field_name_in_item_dt] = max_value[0]

							elif att.match_type == '<=':
								conditions.append(" {field_name_in_item_dt} <=  %({field_name_in_bom_uploader})s ".format(**att_map))
								min_value = frappe.db.sql_list(
									"SELECT max({field_name_in_item_dt}) FROM `tabItem` WHERE custom_material_type = '{0}' AND item_group !='{1}' AND {field_name_in_item_dt} <= %({field_name_in_bom_uploader})s AND {field_name_in_item_dt} > 0".format(item.material_type, sub_assembly_item_group, **att_map),
									item.as_dict()
								)
								if min_value and min_value[0]:
									near_by_value[att_map.field_name_in_item_dt] = min_value[0]

							elif att.match_type == '==':
								conditions.append(" ( {} = %({})s ) ".format(att_map.field_name_in_item_dt, att_map.field_name_in_bom_uploader))
						
						# print(conditions, "---------------------conditionsss------", attr_doc.name)
						if conditions:
							sql = sql + " AND " + " AND ".join(conditions)

						# print(sql, "--------------sql----------------------")
						matched_items = frappe.db.sql(sql, item.as_dict(), pluck='name')
						# print(matched_items, "========matched_items=====")

						final_matched_items = []
						# exact_matched_items = []
						if len(matched_items) > 0:
							if near_by_value:
								# print(near_by_value, "===========near_by_value=======")

								for i in matched_items:
									item_doc = frappe.get_doc('Item', i)
									# item_values = {}

									for key, value in near_by_value.items():
										# item_values[key] = item_doc.get(key)
										if key in item_doc.as_dict() and item_doc.get(key) == value:
											if item_doc.name not in final_matched_items:
												final_matched_items.append(item_doc.name)
												continue
									
									# print(item_values, "----------------item_values------------")
									# if near_by_value == item_values:
									# 	exact_matched_items.append(item_doc.name)

								# print(exact_matched_items, "==================exact_matched_items=============")	

							# print(final_matched_items, "===================final_matched_items=============")
							if len(final_matched_items) > 0:
								item.matched_item_list = ','.join(final_matched_items)
								if len(final_matched_items) == 1:
									item.matched_item_list = final_matched_items[0]
									item.matched_item = final_matched_items[0]
									
								else:
									item.status = "Multi Match"
								

							else:
								item.matched_item_list = ','.join(matched_items)
								if len(matched_items) == 1:
									item.matched_item_list = matched_items[0]
									item.matched_item = matched_items[0]
									# item.status = "Match"
								else:
									item.status = "Multi Match"

							if item.matched_item:
								item_group, custom_wmf = frappe.db.get_value("Item", item.matched_item, ["item_group", "custom_wmf"])
								item.matched_item_group = item_group
								item.item_wmf = custom_wmf
								item.status = "Match"
						
						else:
							item.status = "Not Found"

				count += 1
				frappe.publish_progress(count/len(self.bom_item_details_mw) * 100, title='Finding Matching Items', description='')						

	def check_if_item_is_bought_out(self):
		if len(self.bom_item_details_mw) > 0:
			for item in self.bom_item_details_mw:
				if item.item_level == "Level 2" and item.matched_item:
					item_group = frappe.db.get_value('Item', item.matched_item, 'item_group')
					default_item_group_for_bought_out = frappe.db.get_single_value('Mechwell Setting MW', 'default_item_group_for_bought_out')
					if not default_item_group_for_bought_out:
						frappe.throw(_("Please set Default Item Group for Bought Out In Mechwell Settings Doctype."))

					is_bought_out = check_if_item_group_is_bought_out(default_item_group_for_bought_out, item_group)
					# print(is_bought_out, "===============is_bought_out=============")
					if is_bought_out:
						item.is_bought_out = 'Yes'
					else:
						item.is_bought_out = 'No'
	
	def calculate_raw_material_weight(self):

		total_raw_weight = 0
		for item in self.bom_item_details_mw:
			if item.item_level == "Level 2" and item.matched_item:
				if item.is_bought_out == "Yes":
					item.raw_material_weight = item.qty * (item.item_wmf or 0) 
				else:
					# print(item.matched_item, "========item.matched_item_list====")
					ig, wmf = frappe.db.get_value("Item", item.matched_item, ["item_group", "custom_wmf"])
					item_group = frappe.get_doc('Item Group', ig)
					formula = item_group.custom_raw_material_weight_formula
					formula_params = {
						'L': item.length or 0,
						'W': item.width or 0,
						'T': item.thickness or 0,
						'D': item_group.custom_density or 0,
						'OD' : item.od or 0,
						'ID' : item.id or 0,
						'WPM' : wmf or 0,
						'PPW' : wmf or 0,
						'TP' : item.qty or 0,
						'π': 3.14
					}
					if item_group.custom_is_od_formula_exists == 1 and item.od:
						formula = item_group.custom_od_based_weight_formula.strip() or None
					else:
						formula = item_group.custom_raw_material_weight_formula.strip() or None

					if not formula:
						frappe.throw(_("Please set Raw Material Weight Formula in Item Group <b>{0}</b>").format(get_link_to_form("Item Group", item_group.name)))
						
					total_weight = frappe.safe_eval(formula, None, formula_params)

					# print(total_weight, "-----------total_weight-----------")
					item.raw_material_weight = total_weight or 0

				total_raw_weight = total_raw_weight + (item.raw_material_weight or 0)
				self.total_weight = total_raw_weight

	def check_if_all_matched_items_found(self):
		if len(self.bom_item_details_mw) > 0:
			item_not_found = []
			for row in self.bom_item_details_mw:
				if not row.matched_item and row.item_level == "Level 2":
					item_not_found.append(cstr(row.idx))
			
			# print(item_not_found, "==========item_not_found======")
			if len(item_not_found) > 0:
				frappe.throw(_("For Below Row Numbers Match Item Not Found.<br> <b>{0}</b>").format(", ".join((ele if ele != None else "") for ele in item_not_found)))

	def make_sub_assembly_items(self):
		if len(self.bom_item_details_mw) > 0:
			sub_assembly_item_group = frappe.db.get_single_value('Mechwell Setting MW', 'default_item_group_for_sub_assembly')
			for row in self.bom_item_details_mw:
				if row.is_bought_out != "Yes":
					new_item = frappe.new_doc("Item")
					new_item.item_code = row.parent_fg + "-" + row.sr_no
					new_item.item_name = row.description
					new_item.item_group = sub_assembly_item_group
					# new_item.is_stock_item = 1
					# new_item.stock_uom = "Nos"
					# new_item.custom_material_type = row.material_type
					new_item.custom_length = row.length
					new_item.custom_width = row.width
					new_item.custom_outer_diameter = row.od
					new_item.custom_inner_diameter = row.id
					new_item.custom_thickness = row.thickness

					new_item.save(ignore_permissions=True)

					row.sub_assembly_item = new_item.name

	def make_bom_creator(self):
		if len(self.bom_item_details_mw) > 0:
			bom = frappe.new_doc("BOM Creator")
			bom.__newname = self.name
			bom.name = self.name
			bom.item_code = self.dam_code
			bom.qty = 1
			bom.custom_bom_uploader_ref = self.name
			bom.project = self.project

			for row in self.bom_item_details_mw:
				item = bom.append("items", {})
				parent_idx = frappe.db.get_value("BOM Item Details MW", {"sub_assembly_item": row.parent_fg}, "idx")

				item.fg_item = row.parent_fg
				item.qty = row.qty
				item.custom_sr_no = row.sr_no
				item.parent_row_no = parent_idx
				if row.gad_mfg == "GAD":
						item.allow_alternative_item = 0
				else:
					item.allow_alternative_item = 1

				if row.is_bought_out == "Yes":
					item.item_code = row.matched_item
					item.custom_is_bought_out = row.is_bought_out
					item.qty = row.raw_material_weight

					# print(item.item_code, "=============== Bought out=======")

				else:
					item.item_code = row.sub_assembly_item
					# print(item.item_code, "===============")
					item.is_expandable = 1
					# print(row.parent_fg, item.parent_row_no, "================item.parent_row_no================", parent_idx)

					if row.matched_item and row.item_level == "Level 2":
						raw_item = bom.append("items", {})
						raw_item.item_code = row.matched_item
						raw_item.fg_item = item.item_code
						raw_item.qty = row.raw_material_weight
						raw_item.parent_row_no = item.idx
						print(raw_item.parent_row_no, "================raw_item.parent_row_no")
						if row.gad_mfg == "GAD":
							raw_item.allow_alternative_item = 0
						else:
							raw_item.allow_alternative_item = 1
						
			bom.save(ignore_permissions=True)

	def delete_all_sub_assembly_items(self):
		bom_creator = frappe.db.get_value("BOM Creator", {"custom_bom_uploader_ref": self.name}, "name")
		# print(bom_creator, "=========bom_creator=======")
		if len(self.bom_item_details_mw) > 0 and not bom_creator:
			for row in self.bom_item_details_mw:
				if row.sub_assembly_item:
					sub_assembly_item = frappe.get_doc("Item", row.sub_assembly_item)
					# print(sub_assembly_item.name, "============sub_assembly_item======")
					row.sub_assembly_item = ""
					sub_assembly_item.delete()
				
			frappe.msgprint("Sub Assembly Items Are Deleted", alert=1)


def check_if_item_group_is_bought_out(default_item_group_for_bought_out, item_group):
	if item_group == default_item_group_for_bought_out:
		return True
	elif item_group != default_item_group_for_bought_out:
		parent_item_group = frappe.db.get_value('Item Group', item_group, 'parent_item_group')
		if parent_item_group == default_item_group_for_bought_out:
			return True
		elif not parent_item_group:
			return False
		elif parent_item_group and parent_item_group != default_item_group_for_bought_out:
			check_if_item_group_is_bought_out(default_item_group_for_bought_out, parent_item_group)
	
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
	sheet.column_dimensions['C'].width = 10
	sheet.column_dimensions['D'].width = 20
	sheet.column_dimensions['E'].width = 10
	sheet.column_dimensions['F'].width = 10
	sheet.column_dimensions['G'].width = 10
	sheet.column_dimensions['H'].width = 10
	sheet.column_dimensions['I'].width = 10
	sheet.column_dimensions['J'].width = 20
	sheet.column_dimensions['K'].width = 10
	sheet.column_dimensions['L'].width = 10
	sheet.column_dimensions['M'].width = 10

	bg_fill = PatternFill(fill_type='solid', start_color='FF474C', end_color='FF474C')

	cells_to_style = ['A8', 'B8', 'C8','D8', 'J8', 'K8', 'L8']
	for cell_coord in cells_to_style:
		cell = sheet[cell_coord]
		cell.fill = bg_fill

	xlsx_file = BytesIO()
	workbook.save(xlsx_file)

	provide_binary_file(doc.name, 'xlsx', xlsx_file.getvalue())
