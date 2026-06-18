import frappe
import frappe.desk.query_report as _qr

# Hold a reference to the original run before any patching
_original_run = _qr.run


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
	result = _original_run(
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


@frappe.whitelist()
def export_query():
	# _export_query calls run() by name inside the module, bypassing the
	# whitelisted override. Temporarily swap it so the export picks up our
	# enriched version, then always restore the original.
	_qr.run = run
	try:
		return _qr.export_query()
	finally:
		_qr.run = _original_run


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
		and row.get("account")
	]

	if not je_rows:
		return

	je_names = list({row["voucher_no"] for row in je_rows})

	# Fetch all JE Account remarks grouped by (parent, account)
	jea_rows = frappe.db.get_all(
		"Journal Entry Account",
		filters={"parent": ["in", je_names]},
		fields=["parent", "account", "user_remark"],
	)

	# Build map: (voucher_no, account) -> [distinct non-empty remarks]
	remark_map = {}
	for r in jea_rows:
		if not r.user_remark:
			continue
		key = (r.parent, r.account)
		if key not in remark_map:
			remark_map[key] = []
		remark = r.user_remark.strip()
		if remark and remark not in remark_map[key]:
			remark_map[key].append(remark)

	for row in data:
		if not isinstance(row, dict):
			continue
		if row.get("voucher_type") != "Journal Entry":
			continue

		key = (row.get("voucher_no"), row.get("account"))
		parts = remark_map.get(key, [])
		row["je_user_remark"] = "[" + ", ".join(parts) + "]" if parts else ""
