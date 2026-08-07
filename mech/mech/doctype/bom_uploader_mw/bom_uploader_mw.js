// Copyright (c) 2025, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("BOM Uploader MW", {
	refresh(frm) {
		$('.grid-add-row').hide()
		$('.grid-remove-rows').hide()
		$('.grid-download').hide()
		$('.grid-upload').hide()
		$('.grid-add-multiple-rows').hide()
		hideGridRowFormButtons()
		if (frm.is_new()) {
			frm.dashboard.add_comment(__("<b>Please save the form to download excel for import</b>"), "blue", true);
		}

		// Button to create BOM Creator
		if (!frm.doc.bom_creator_ref && frm.doc.bom_creator_ref != '' && frm.doc.bom_item_details_mw.length > 1) {
			frm.add_custom_button(__("Create BOM Creator"), () => {
				frm.call({
					method: 'validate_conditions_and_create_bom_creator',
					doc: frm.doc,
					freeze: true,
					freeze_message: __('Validating and Creating BOM Creator...'),
				})
			}).css({ "background-color": "#0b5ed7", "color": "#fff" });
		}

		render_bom_tree(frm);
	},
	after_save(frm) {
		frm.reload_doc();
	},
	dam_code(frm) {
		if (frm.doc.dam_code) {
			frm.call('get_sales_order')
		}
		else {
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
				add_table: false
			}
		);
	},
	download_bom_item_details_excel(frm) {
		open_url_post(
			"/api/method/mech.mech.doctype.bom_uploader_mw.bom_uploader_mw.download_formatted_excel",
			{
				name: frm.doc.name,
				add_table: true
			}
		);
	},
	bom_item_details_mw_add(frm) {
		render_bom_tree(frm);
	},
	bom_item_details_mw_remove(frm) {
		render_bom_tree(frm);
	},
});

// Hide the grid row form buttons (add, delete, move, duplicate)
function hideGridRowFormButtons() {
	if ($('#bom-uploader-hide-row-form-buttons').length) return
	$('head').append(`
		<style id="bom-uploader-hide-row-form-buttons">
            div[data-page-route="BOM Uploader MW"] .grid-insert-row,
            div[data-page-route="BOM Uploader MW"] .grid-insert-row-below,
            div[data-page-route="BOM Uploader MW"] .grid-duplicate-row,
            div[data-page-route="BOM Uploader MW"] .grid-move-row,
            div[data-page-route="BOM Uploader MW"] .grid-append-row,
            div[data-page-route="BOM Uploader MW"] .grid-delete-row {
                display: none !important;
            }
        </style>
		`)
}

/////////////////// Tree Preview + Drag & Drop ///////////////////

const BOM_TREE_STATUS_COLOR = {
	"Match": "green",
	"Multi Match": "orange",
	"Not Found": "red",
};

function sync_and_build_tree(frm) {
	const rows = frm.doc.bom_item_details_mw || [];
	const dam_code = frm.doc.dam_code;
	const children_map = {};
	const root_children = [];
	const unassigned = [];
	const stack = [];
	const code_rows = {}; // sub_assembly_item -> row, every non-leaf row ever seen (survives sibling resets, so a row's children can be entered later, out of strict depth-first order)

	rows.forEach((row) => {
		let parent_row = null;
		let is_root = false;

		if (row.parent_fg === dam_code) {
			stack.length = 0;
			is_root = true;
		} else {
			while (stack.length && stack[stack.length - 1].code !== row.parent_fg) {
				stack.pop();
			}
			if (stack.length) {
				parent_row = stack[stack.length - 1].row;
			} else if (code_rows[row.parent_fg]) {
				parent_row = code_rows[row.parent_fg];
			}
		}

		if (is_root) {
			root_children.push(row);
			row.level = 1;
		} else if (parent_row) {
			children_map[parent_row.name] = children_map[parent_row.name] || [];
			children_map[parent_row.name].push(row);
			row.level = (parent_row.level || 1) + 1;
		} else {
			unassigned.push(row);
			row.level = row.level || 1;
		}

		if (row.sub_assembly_item) {
			stack.push({ code: row.sub_assembly_item, row: row });
			code_rows[row.sub_assembly_item] = row;
		}
	});

	rows.forEach((row) => {
		row.is_leaf_item = (children_map[row.name] || []).length > 0 ? 0 : 1;
	});

	return { children_map, root_children, unassigned };
}

function get_subtree_length(rows, start_index) {
	const base_level = rows[start_index].level || 1;
	let count = 1;
	for (let i = start_index + 1; i < rows.length; i++) {
		if ((rows[i].level || 1) > base_level) {
			count++;
		} else {
			break;
		}
	}
	return count;
}

function reindex_rows(rows) {
	rows.forEach((r, i) => {
		r.idx = i + 1;
	});
}

function render_bom_tree(frm) {
	if (!frm.fields_dict["bom_tree_preview"]) return;

	const $wrapper = $(frm.fields_dict["bom_tree_preview"].wrapper);
	// remember which nodes are expanded so an in-session re-render (select
	// item, add/delete, drag & drop, qty edit) doesn't collapse the tree back
	const open_row_names = capture_open_row_names($wrapper);
	$wrapper.empty();

	const rows = frm.doc.bom_item_details_mw || [];
	if (!rows.length) {
		return;
	}

	const { children_map, root_children, unassigned } = sync_and_build_tree(frm);

	// inject tree specific styles (scoped, rebuilt with wrapper every render)
	$(`
		<style>
			.bom-uploader-tree .tree-link { user-select: none; }
			.bom-uploader-tree .tree-link.bom-tree-parent,
			.bom-uploader-tree .tree-link.bom-tree-leaf,
			.bom-uploader-tree .tree-link.bom-tree-root { cursor: grab; }
			.bom-uploader-tree .tree-link.dragging { opacity: 0.4; }
			.bom-uploader-tree .tree-link.tree-drop-hover {
				background-color: var(--highlight-color);
				outline: 1px dashed var(--dark-border-color);
				border-radius: var(--border-radius-sm);
			}
			.bom-uploader-tree .status-dot {
				display: inline-block;
				width: 7px;
				height: 7px;
				border-radius: 50%;
				margin-right: 6px;
			}
			.bom-uploader-tree .status-dot.green { background-color: var(--green-500); }
			.bom-uploader-tree .status-dot.orange { background-color: var(--orange-500); }
			.bom-uploader-tree .status-dot.red { background-color: var(--red-500); }
			.bom-uploader-tree .tree-node-toolbar {
				display: none;
				margin-left: 10px;
				vertical-align: middle;
			}
			.bom-uploader-tree .tree-link:hover .tree-node-toolbar { display: inline-flex; }
			.bom-uploader-tree .tree-node-toolbar .tree-toolbar-button.text-danger { color: var(--red-500); }
			.bom-uploader-tree .bom-qty-pill {
				display: inline-flex;
				align-items: center;
				background-color: var(--bg-white);
				color: var(--text-on-gray);
				border: 1px solid var(--bg-gray);
				border-radius: 10px;
				padding: 1px 8px;
				margin-left: 8px;
				font-size: 11px;
				font-weight: 450;
			}
			.bom-uploader-tree .bom-qty-pill .weight-value { margin-left: 6px; padding-left: 6px; border-left: 1px solid var(--bg-gray); }
			.bom-uploader-tree .bom-qty-pill .qty-edit-icon { margin-left: 6px; cursor: pointer; opacity: 0.6; }
			.bom-uploader-tree .bom-qty-pill .qty-edit-icon:hover { opacity: 1; }
		</style>
	`).appendTo($wrapper);

	const $tree = $('<div class="tree with-skeleton bom-uploader-tree">').appendTo($wrapper);

	// root node - the DAM code being built
	const $root_node = $('<div class="tree-node opened">').appendTo($tree);
	const $root_link = $(`
		<div class="tree-link bom-tree-root">
			<span class="node-parent">${frappe.utils.icon("folder-open", "md")}</span>
			<a class="tree-label">${frappe.utils.escape_html(frm.doc.dam_code || frm.doc.name || __("All Items"))}</a>
		</div>
	`).appendTo($root_node);
	build_node_toolbar([
		{
			label: frappe.utils.icon("add", "xs") + " " + __("Sub Assembly"),
			on_click: () => add_sub_assembly_node(frm, null),
		},
		// {
		// 	label: frappe.utils.icon("add", "xs") + " " + __("Raw Material"),
		// 	on_click: () => add_raw_material_node(frm, null),
		// },
	]).appendTo($root_link);
	const $root_children_ul = $('<ul class="tree-children">').appendTo($root_node);
	setup_drop_target($root_link, null, frm);

	root_children.forEach((row) => append_node($root_children_ul, row));

	if (unassigned.length) {
		const $li = $('<li class="tree-node opened">').appendTo($root_children_ul);
		$(`
			<div class="tree-link">
				<span class="node-parent">${frappe.utils.icon("folder-normal", "md")}</span>
				<a class="tree-label text-muted">${__("Unassigned")}</a>
			</div>
		`).appendTo($li);
		const $children = $('<ul class="tree-children">').appendTo($li);
		unassigned.forEach((row) => append_node($children, row));
	}

	function append_node($parent_ul, row) {
		if (!row.is_leaf_item) {
			append_parent_node($parent_ul, row);
		} else {
			append_leaf_node($parent_ul, row);
		}
	}

	function append_parent_node($parent_ul, row) {
		const $li = $('<li class="tree-node">').appendTo($parent_ul);
		const group_name = row.user_input || row.description || "";
		const group_label = (row.sub_assembly_item || "") + (group_name ? ` (${group_name})` : "");
		const $link = $(`
			<div class="tree-link bom-tree-parent" draggable="true" data-row-name="${row.name}">
				<span class="node-parent">${frappe.utils.icon("folder-normal", "md")}</span>
				<a class="tree-label">${frappe.utils.escape_html(group_label)}</a>
			</div>
		`).appendTo($li);

		build_node_toolbar([
			{
				label: frappe.utils.icon("add", "xs") + " " + __("Sub Assembly"),
				on_click: () => add_sub_assembly_node(frm, row),
			},
			// {
			// 	label: frappe.utils.icon("add", "xs") + " " + __("Raw Material"),
			// 	on_click: () => add_raw_material_node(frm, row),
			// },
			{
				label: frappe.utils.icon("delete", "xs"),
				class_name: "text-danger",
				on_click: () => delete_tree_node(frm, row),
			},
		]).appendTo($link);

		const $children_ul = $('<ul class="tree-children">').appendTo($li).hide();
		(children_map[row.name] || []).forEach((child) => append_node($children_ul, child));

		if (open_row_names.has(row.name)) {
			open_single_level($li.get(0));
		}

		let suppress_click = false;
		$link.on("click", () => {
			if (suppress_click) {
				suppress_click = false;
				return;
			}
			set_recursive_open($li.get(0), !$li.hasClass("opened"));
		});

		$link.on("dragstart", (e) => {
			e.stopPropagation();
			e.originalEvent.dataTransfer.setData("text/plain", row.name);
			e.originalEvent.dataTransfer.effectAllowed = "move";
			$link.addClass("dragging");
		});
		$link.on("dragend", () => {
			$link.removeClass("dragging");
			suppress_click = true;
		});

		setup_drop_target($link, row, frm);
	}

	function append_leaf_node($parent_ul, row) {
		// raw material "slot" - the actual BOM Item Details MW row (drag source, add/delete target)
		const $li = $('<li class="tree-node">').appendTo($parent_ul);
		const slot_name = row.user_input || row.description || "";
		const slot_label = (row.sub_assembly_item || "") + (slot_name ? ` (${slot_name})` : "");
		const $link = $(`
			<div class="tree-link bom-tree-leaf" draggable="true" data-row-name="${row.name}">
				<span class="node-parent">${frappe.utils.icon("folder-normal", "md")}</span>
				<a class="tree-label">${frappe.utils.escape_html(slot_label)}</a>
			</div>
		`).appendTo($li);

		build_node_toolbar([
			{
				label: __("Select Item"),
				on_click: () => open_choose_item_dialog(frm, row),
			},
			{
				label: frappe.utils.icon("delete", "xs"),
				class_name: "text-danger",
				on_click: () => delete_tree_node(frm, row),
			},
		]).appendTo($link);

		let suppress_click = false;
		$link.on("dragstart", (e) => {
			e.stopPropagation();
			e.originalEvent.dataTransfer.setData("text/plain", row.name);
			e.originalEvent.dataTransfer.effectAllowed = "move";
			$link.addClass("dragging");
		});
		$link.on("dragend", () => {
			$link.removeClass("dragging");
			suppress_click = true;
		});

		// matched raw material - shown as its own child node, not squeezed onto the slot's line
		const $matched_ul = $('<ul class="tree-children">').appendTo($li).hide();
		const $matched_li = $('<li class="tree-node">').appendTo($matched_ul);
		const color = BOM_TREE_STATUS_COLOR[row.status] || "";
		const matched_label = row.matched_item
			? row.matched_item
			: row.status === "Multi Match"
			? __("Multiple Matches Found")
			: __("Not Found");
		const $matched_link = $(`
			<div class="tree-link bom-tree-matched-item">
				${color ? `<span class="status-dot ${color}"></span>` : `<span class="node-parent">${frappe.utils.icon("primitive-dot", "xs")}</span>`}
				<a class="tree-label ${row.matched_item ? "" : "text-muted"}">${frappe.utils.escape_html(matched_label)}</a>
			</div>
		`).appendTo($matched_li);

		const $pill = $(`
			<span class="bom-qty-pill">
				<span class="qty-value">${frappe.utils.escape_html(frappe.format(row.qty || 0, { fieldtype: "Float" }, { only_value: true }))}</span>
				<span class="weight-value text-muted">${frappe.utils.escape_html(frappe.format(row.raw_material_weight || 0, { fieldtype: "Float", precision: 2 }, { only_value: true }))} kg</span>
			</span>
		`).appendTo($matched_link);

		$(`<span class="qty-edit-icon">${frappe.utils.icon("edit", "xs")}</span>`)
			.appendTo($pill)
			.on("click", (e) => {
				e.preventDefault();
				e.stopPropagation();
				edit_leaf_qty(frm, row);
			});

		if (open_row_names.has(row.name)) {
			open_single_level($li.get(0));
		}

		$link.on("click", () => {
			if (suppress_click) {
				suppress_click = false;
				return;
			}
			set_recursive_open($li.get(0), !$li.hasClass("opened"));
		});
	}

	function setup_drop_target($link, target_row_or_null, frm) {
		$link.on("dragover", (e) => {
			e.preventDefault();
			e.stopPropagation();
			e.originalEvent.dataTransfer.dropEffect = "move";
			$link.addClass("tree-drop-hover");
		});
		$link.on("dragleave", () => $link.removeClass("tree-drop-hover"));
		$link.on("drop", (e) => {
			e.preventDefault();
			e.stopPropagation();
			$link.removeClass("tree-drop-hover");

			const row_name = e.originalEvent.dataTransfer.getData("text/plain");
			if (!row_name) return;

			const dragged_row = locals["BOM Item Details MW"][row_name];
			if (!dragged_row) return;
			if (target_row_or_null && dragged_row.name === target_row_or_null.name) return;

			reparent_row(frm, dragged_row, target_row_or_null);
		});
	}
}

/////////////////// Add / Delete / Move Tree Nodes ///////////////////
// so opening a parent reveals its whole subtree instead of just its
// immediate (still-collapsed) children.
function set_recursive_open(li_el, opening) {
	const $li = $(li_el);
	const $link = $li.children(".tree-link");
	const $children_ul = $li.children(".tree-children");
	const $icon = $link.find(".node-parent");

	$li.toggleClass("opened", opening);
	$children_ul.toggle(opening);
	if ($icon.length && $children_ul.length) {
		$icon.html(frappe.utils.icon(opening ? "folder-open" : "folder-normal", "md"));
	}

	$children_ul.children(".tree-node").each(function () {
		set_recursive_open(this, opening);
	});
}

// Snapshot of which rows are currently expanded, keyed by row.name (the
// same identity used everywhere else in the tree), read from the DOM right
// before a re-render wipes it.
function capture_open_row_names($wrapper) {
	const names = new Set();
	$wrapper.find(".tree-node.opened").each(function () {
		const row_name = $(this).children(".tree-link").attr("data-row-name");
		if (row_name) names.add(row_name);
	});
	return names;
}

// Re-applies a single node's own open state (no cascading to children) -
// used to replay a captured snapshot exactly, without force-opening
// children that the user had deliberately left collapsed.
function open_single_level(li_el) {
	const $li = $(li_el);
	const $link = $li.children(".tree-link");
	const $children_ul = $li.children(".tree-children");
	const $icon = $link.find(".node-parent");

	$li.addClass("opened");
	$children_ul.show();
	if ($icon.length && $children_ul.length) {
		$icon.html(frappe.utils.icon("folder-open", "md"));
	}
}

function build_node_toolbar(buttons) {
	const $toolbar = $('<span class="tree-node-toolbar btn-group">');
	buttons.forEach(({ label, class_name, on_click }) => {
		$(`<button class="btn btn-default btn-xs tree-toolbar-button ${class_name || ""}"></button>`)
			.html(label)
			.appendTo($toolbar)
			.on("click", (e) => {
				e.preventDefault();
				e.stopPropagation();
				on_click();
			});
	});
	return $toolbar;
}

function next_level1_sr_no(siblings) {
	const used = siblings.filter((r) => !r.is_leaf_item).map((r) => r.sr_no);
	const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
	for (const ch of letters) {
		if (!used.includes(ch)) return ch;
	}
	let n = 1;
	while (used.includes(`X${n}`)) n++;
	return `X${n}`;
}

function next_level2_sr_no(siblings) {
	const used = siblings.filter((r) => r.is_leaf_item).map((r) => r.sr_no);
	let n = 1;
	while (used.includes(String(n))) n++;
	return String(n);
}

function insert_row_as_last_child(frm, parent_row_or_null, row_data) {
	const new_row = frm.add_child("bom_item_details_mw", row_data);
	const rows = frm.doc.bom_item_details_mw;
	rows.pop(); // frm.add_child appended it at the end - pull it back out to reposition

	let insert_index;
	if (parent_row_or_null) {
		const parent_index = rows.findIndex((r) => r.name === parent_row_or_null.name);
		insert_index = parent_index + get_subtree_length(rows, parent_index);
	} else {
		insert_index = rows.length;
	}
	rows.splice(insert_index, 0, new_row);
	reindex_rows(rows);
	return new_row;
}

function add_sub_assembly_node(frm, parent_row_or_null) {
	const tree = sync_and_build_tree(frm);
	const siblings = parent_row_or_null ? tree.children_map[parent_row_or_null.name] || [] : tree.root_children;
	const parent_code = parent_row_or_null ? parent_row_or_null.sub_assembly_item : frm.doc.dam_code;
	const sr_no = next_level1_sr_no(siblings);
	const suggested_code = `${parent_code}-${sr_no}`;

	frappe.prompt(
		[
			{
				label: __("Sub Assembly Item"),
				fieldname: "sub_assembly_item",
				fieldtype: "Data",
				default: suggested_code,
				reqd: 1,
				description: __("Reuse an existing code to place the same sub-assembly here too"),
			},
			{ label: __("User Input"), fieldname: "user_input", fieldtype: "Data" },
			{ fieldtype: "Column Break" },
			{ label: __("Description"), fieldname: "description", fieldtype: "Data", reqd: 1 },
			{ label: __("Material Type"), fieldname: "material_type", fieldtype: "Link", options: "Material Type MW", reqd: 1},
			{ fieldtype: "Section Break" },
			{ label: __("Sr No"), fieldname: "sr_no", fieldtype: "Data", reqd: 1},
			{ label: __("Matched Item"), fieldname: "matched_item", fieldtype: "Link", options: "Item" },
			{ fieldtype: "Column Break" },
			{ label: __("Qty"), fieldname: "qty", fieldtype: "Float", default: 1, reqd: 1 },
			{ label: __("GAD/MFG"), fieldname: "gad_mfg", fieldtype: "Select", options: ["GAD", "MFG"], reqd: 1 },
			{ fieldtype: "Section Break" },
			{ label: __("Length"), fieldname: "length", fieldtype: "Float" },
			{ label: __("Width"), fieldname: "width", fieldtype: "Float" },
			{ fieldtype: "Column Break" },
			{ label: __("Thickness"), fieldname: "thickness", fieldtype: "Float" },
			{ label: __("OD"), fieldname: "od", fieldtype: "Float" },
			{ label: __("ID"), fieldname: "id", fieldtype: "Float" },
		],
		(values) => {
			insert_row_as_last_child(frm, parent_row_or_null, {
				parent_fg: parent_code,
				sub_assembly_item: values.sub_assembly_item,
				user_input: values.user_input,
				sr_no: values.sr_no,
				description: values.description,
				material_type: values.material_type,
				matched_item: values.matched_item,
				status: values.matched_item ? "Match" : "",
				qty: values.qty,
				gad_mfg: values.gad_mfg,
				length: values.length,
				width: values.width,
				thickness: values.thickness,
				od: values.od,
				id: values.id,
				is_leaf_item: 1
			});
			frm.dirty();
			trigger_recalc_and_render(frm);
			frappe.show_alert({ message: __("Sub Assembly {0} added", [values.sub_assembly_item]), indicator: "green" });
		},
		__("Add Sub Assembly For {0}", [parent_code]),
		__("Add")
	);
}

function add_raw_material_node(frm, parent_row_or_null) {
	const tree = sync_and_build_tree(frm);
	const siblings = parent_row_or_null ? tree.children_map[parent_row_or_null.name] || [] : tree.root_children;
	const parent_code = parent_row_or_null ? parent_row_or_null.sub_assembly_item : frm.doc.dam_code;
	const sr_no = next_level2_sr_no(siblings);

	let dialog = frappe.prompt(
		[
			{
				label: __("Item"),
				fieldname: "item_code",
				fieldtype: "Link",
				options: "Item",
				reqd: 1,
				change() {
					const item_code = this.value;
					if (!item_code) return;
					frappe.db
						.get_value("Item", item_code, ["item_name", "custom_material_type", "custom_length", "custom_width", "custom_thickness", "custom_outer_diameter", "custom_inner_diameter"])
						.then((r) => {
							const item = r.message || {};
							dialog.set_value("description", item.item_name || item_code);
							dialog.set_value("material_type", item.custom_material_type);
							dialog.set_value("length", item.custom_length);
							dialog.set_value("width", item.custom_width);
							dialog.set_value("thickness", item.custom_thickness);
							dialog.set_value("od", item.custom_outer_diameter);
							dialog.set_value("id", item.custom_inner_diameter);
							
						});
				},
			},
			{ label: __("Qty"), fieldname: "qty", fieldtype: "Float", default: 1, reqd: 1 },
			{ fieldtype: "Column Break" },
			{ label: __("Description"), fieldname: "description", fieldtype: "Data" },
			{
				label: __("Material Type"),
				fieldname: "material_type",
				fieldtype: "Link",
				options: "Material Type MW",
				read_only: 1,
			},
			{ fieldtype: "Section Break" },
			{ label: __("Length"), fieldname: "length", fieldtype: "Float" },
			{ label: __("Width"), fieldname: "width", fieldtype: "Float" },
			{ fieldtype: "Column Break" },
			{ label: __("Thickness"), fieldname: "thickness", fieldtype: "Float" },
			{ label: __("OD"), fieldname: "od", fieldtype: "Float" },
			{ label: __("ID"), fieldname: "id", fieldtype: "Float" },
		],
		(values) => {
			insert_row_as_last_child(frm, parent_row_or_null, {
				parent_fg: parent_code,
				sr_no: sr_no,
				description: values.description,
				material_type: values.material_type,
				matched_item: values.item_code,
				status: "Match",
				qty: values.qty,
				length: values.length,
				width: values.width,
				thickness: values.thickness,
				od: values.od,
				id: values.id,
				is_leaf_item: 1,
			});
			frm.dirty();
			trigger_recalc_and_render(frm);
			frappe.show_alert({ message: __("Raw Material {0} added", [sr_no]), indicator: "green" });
		},
		__("Add Raw Material For {0}", [parent_code]),
		__("Add")
	);
}

function delete_tree_node(frm, row) {
	const label =  row.sub_assembly_item || row.description || row.matched_item || row.sr_no || row.name;
	frappe.confirm(__("Are you sure you want to delete {0}?", [label]), () => {
		const rows = frm.doc.bom_item_details_mw;
		const start_index = rows.findIndex((r) => r.name === row.name);
		if (start_index === -1) return;

		const span = get_subtree_length(rows, start_index);
		const removed = rows.splice(start_index, span);
		reindex_rows(rows);

		frm.dirty();
		frm.refresh_field("bom_item_details_mw");
		trigger_recalc_and_render(frm);
		frappe.show_alert({ message: __("Deleted {0} item(s)", [removed.length]), indicator: "green" });
	});
}

function reparent_row(frm, dragged_row, target_parent_row_or_null) {
	const rows = frm.doc.bom_item_details_mw;
	const start_index = rows.findIndex((r) => r.name === dragged_row.name);
	if (start_index === -1) return;

	const new_parent_code = target_parent_row_or_null ? target_parent_row_or_null.sub_assembly_item : frm.doc.dam_code;
	if (dragged_row.parent_fg === new_parent_code) return; // already there, no-op

	const span = get_subtree_length(rows, start_index);
	const block = rows.splice(start_index, span);

	if (target_parent_row_or_null && block.some((r) => r.name === target_parent_row_or_null.name)) {
		// dropped into its own subtree - put it back and abort
		rows.splice(start_index, 0, ...block);
		frappe.show_alert({
			message: __("Cannot move a group under itself or its own sub-item"),
			indicator: "red",
		});
		return;
	}

	block[0].parent_fg = new_parent_code;

	let insert_index;
	if (target_parent_row_or_null) {
		const parent_index = rows.findIndex((r) => r.name === target_parent_row_or_null.name);
		insert_index = parent_index + get_subtree_length(rows, parent_index);
	} else {
		insert_index = rows.length;
	}
	rows.splice(insert_index, 0, ...block);
	reindex_rows(rows);

	frm.dirty();
	frm.refresh_field("bom_item_details_mw");
	trigger_recalc_and_render(frm);

	frappe.show_alert({
		message: __("Moved {0}", [block[0].description || block[0].sub_assembly_item || block[0].sr_no]),
		indicator: "green",
	});
}

function edit_leaf_qty(frm, row) {
	frappe.prompt(
		[{ label: __("Qty"), fieldname: "qty", fieldtype: "Float", default: row.qty, reqd: 1 }],
		(values) => {
			frappe.model.set_value(row.doctype, row.name, "qty", values.qty);
			frm.dirty();
			trigger_recalc_and_render(frm);
		},
		__("Edit Qty"),
		__("Update")
	);
}

function trigger_recalc_and_render(frm) {
	frm.call({
		doc: frm.doc,
		method: "recalculate_bom_weights",
		callback: () => {
			frm.refresh_field("bom_item_details_mw");
			frm.refresh_field("total_weight");
			render_bom_tree(frm);
		},
	});
}

/////////////////// Multiple Matched Item ///////////////////

frappe.ui.form.on("BOM Item Details MW", {
	choose_item: function (frm, cdt, cdn) {
		open_choose_item_dialog(frm, locals[cdt][cdn]);
	},
})

function open_choose_item_dialog(frm, row) {
	let dialog = undefined
	const dialog_field = []

	attribute_fields = [
			{
				fieldtype: "Data",
				fieldname: "material_type",
				label: "Material Type",
				read_only: 1,
				default: row.material_type || ""
			},
			{
				fieldtype: "Data",
				fieldname: "length",
				label: "Length",
				read_only: 1,
				default: row.length || ""
			},
			{
				fieldtype: "Data",
				fieldname: "width",
				label: "Width",
				read_only: 1,
				default: row.width || ""
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Data",
				fieldname: "thickness",
				label: "Thickness",
				read_only: 1,
				default: row.thickness || ""
			},
			{
				fieldtype: "Data",
				fieldname: "od",
				label: "OD",
				read_only: 1,
				default: row.od || ""
			},
			{
				fieldtype: "Data",
				fieldname: "id",
				label: "ID",
				read_only: 1,
				default: row.id || ""
			},
			{ fieldtype: "Section Break" },
		]

	let sub_assembly_item_group = ""
		frappe.db.get_single_value('Mechwell Setting MW', 'default_item_group_for_sub_assembly')
			.then(item_group => {
				sub_assembly_item_group = item_group
			})

	if (row.status == "Not Found" || (row.status == "Match" && (!row.matched_item_list || row.matched_item_list == ''))){
		dialog_field.push(...attribute_fields)
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
			{ fieldtype: "Column Break" },
		)
	}

	else if (row.matched_item_list) {
		let str = row.matched_item_list || "";
		let array = str.split(",").map(s => s.trim().replace(/'/g, ''));

		if (array.length === 1 ) {
			dialog_field.push(...attribute_fields)
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
			{ fieldtype: "Column Break" },
		)
			// frappe.show_alert({
			// message:__('Matched Item already Selected'),
			// indicator:'green'
			// }, 5);
		}

		else if (array.length > 1) {
		dialog_field.push(...attribute_fields)
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
			{ fieldtype: "Column Break" },
		)
	}
	}
	if (dialog_field.length > 0){
		dialog = new frappe.ui.Dialog({
			title: __("Select Raw Material for {0}", [row.sub_assembly_item || row.description || row.sr_no || row.name]),
			fields: dialog_field,
			primary_action_label: 'Get Items',
			primary_action: function (values) {
				if (values){
					let selected_item = values.select_item;
					frappe.model.set_value(row.doctype, row.name, 'matched_item', selected_item);
					frappe.model.set_value(row.doctype, row.name, 'status', 'Match');
					frm.dirty();
					trigger_recalc_and_render(frm);
				}
				dialog.hide();
			}
		})
	dialog.show()
	}
}
