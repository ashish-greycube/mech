# Copyright (c) 2026, GreyCube Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint

def execute(filters=None):
    if not filters : filters = {}
    columns, data = [], []
 
    columns = get_columns()
    data = get_data(filters)
 
    if not data :
        msgprint('No Records Found')
        return columns, data

    return columns, data


def get_columns():
    return [
        {
            "fieldname" : "item_code",
            "fieldtype" : "Link",
            "label" : _("Item Code"),
            "options" : "Item",
            'width' : '120'
        },
        {
            "fieldname" : "item_group",
            "fieldtype" : "Link",
            "label" : _("Item Group"),
            "options" : "Item Group",
            'width' : '120'
        },
        {
            "fieldname" : "material_type",
            "fieldtype" : "Link",
            "label" : _("Material Type"),
            "options" : "Material Type MW",
            'width' : '250'
        },
        {
            "fieldname" : "attribute",
            "fieldtype" : "Link",
            "label" : _("Attribute"),
            "options" : "Attribute MW",
            'width' : '200'
        },
        {
            "fieldname" : "match_type",
            "fieldtype" : "Data",
            "label" : _("Match Type"),
            'width' : '120'
        },
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    return frappe.db.sql("""
        SELECT
            i.name AS item_code,
            i.item_group AS item_group,
            IFNULL(i.custom_material_type, '-') AS material_type,
            IFNULL(dt.attribute, '-') AS attribute,
            IFNULL(dt.match_type, '-') AS match_type
        FROM `tabItem` i
        LEFT JOIN 
            (SELECT mt.name AS name , tm.attribute AS attribute, tm.match_type AS match_type
            FROM
            `tabMaterial Type MW` mt
            LEFT JOIN `tabMaterial Attributes MW` tm
             ON mt.name = tm.parent 
            ) dt
        ON i.custom_material_type = dt.name
        WHERE i.disabled=0 {0}
    """.format(conditions), as_dict=1, debug=1)

def get_conditions(filters):
    conditions = ""

    if filters.get("item_group"):
        conditions += " AND i.item_group = '{0}'".format(filters["item_group"])

    if filters.get("material_type"):
        conditions += " AND i.custom_material_type ='{0}'".format(filters["material_type"])
        
    return conditions