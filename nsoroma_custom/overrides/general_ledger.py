import frappe


@frappe.whitelist()
def run(
	report_name,
	filters=None,
	user=None,
	ignore_prepared_report=False,
	custom_columns=None,
	is_tree=False,
	parent_field=None,
	are_default_filters=True,
):
	from frappe.desk.query_report import run as _run

	result = _run(
		report_name=report_name,
		filters=filters,
		user=user,
		ignore_prepared_report=ignore_prepared_report,
		custom_columns=custom_columns,
		is_tree=is_tree,
		parent_field=parent_field,
		are_default_filters=are_default_filters,
	)

	if report_name == "General Ledger":
		_inject_je_remarks(result)

	return result


def _inject_je_remarks(result):
	columns = result.get("columns", [])
	data = result.get("result", [])

	columns.append({
		"label": "JE Remarks",
		"fieldname": "je_user_remark",
		"fieldtype": "Data",
		"width": 300,
	})

	je_rows = [
		row for row in data
		if isinstance(row, dict)
		and row.get("voucher_type") == "Journal Entry"
		and row.get("voucher_no")
	]

	if not je_rows:
		return

	# Fetch JE header user_remark
	je_names = list({row["voucher_no"] for row in je_rows})
	je_header_remarks = {
		r.name: r.user_remark or ""
		for r in frappe.db.get_all(
			"Journal Entry",
			filters={"name": ["in", je_names]},
			fields=["name", "user_remark"],
		)
	}

	# Fetch voucher_detail_no from GL Entry to reach the specific JE Account row
	gl_names = [row["gl_entry"] for row in je_rows if row.get("gl_entry")]
	gle_detail_map = {}
	if gl_names:
		for r in frappe.db.get_all(
			"GL Entry",
			filters={"name": ["in", gl_names]},
			fields=["name", "voucher_detail_no"],
		):
			if r.voucher_detail_no:
				gle_detail_map[r.name] = r.voucher_detail_no

	# Fetch JE Account line user_remark
	jea_names = list(set(gle_detail_map.values()))
	jea_line_remarks = {}
	if jea_names:
		for r in frappe.db.get_all(
			"Journal Entry Account",
			filters={"name": ["in", jea_names]},
			fields=["name", "user_remark"],
		):
			jea_line_remarks[r.name] = r.user_remark or ""

	# Combine header + line remarks per GL row
	for row in data:
		if not isinstance(row, dict):
			continue
		if row.get("voucher_type") != "Journal Entry":
			continue

		header_remark = je_header_remarks.get(row.get("voucher_no"), "")
		jea_name = gle_detail_map.get(row.get("gl_entry"), "")
		line_remark = jea_line_remarks.get(jea_name, "") if jea_name else ""

		parts = []
		if header_remark:
			parts.append(header_remark)
		# Only add line remark if it differs from the header remark
		if line_remark and line_remark != header_remark:
			parts.append(line_remark)

		row["je_user_remark"] = "[" + ", ".join(parts) + "]" if parts else ""
