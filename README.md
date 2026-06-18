## Nsoroma Custom

Custom overrides and builds for NsoromaGPS. This app contains all site-level customizations that extend ERPNext/Frappe behavior without modifying upstream app code.

---

### Installation

```bash
bench get-app git@github.com:NsoromaReceiving/nsoroma_custom.git
bench --site <site> install-app nsoroma_custom
bench restart
```

---

### Overrides

#### General Ledger — JE Remarks Column

**File:** `nsoroma_custom/overrides/general_ledger.py`

Adds a **JE Remarks** column to the standard General Ledger report. The column is populated only for rows where the voucher type is `Journal Entry`, pulling remarks from two sources:

| Source | Field | Level |
|--------|-------|-------|
| Journal Entry | `user_remark` | Header (applies to all GL lines from that JE) |
| Journal Entry Account | `user_remark` | Per line (specific to that GL entry) |

Displayed as `[header remark, line remark]`. If both are identical only one is shown. Non-JE rows (Sales Invoice, Purchase Invoice, etc.) are left blank.

**Approach:** Uses Frappe's `override_whitelisted_methods` hook to wrap `frappe.desk.query_report.run`. Only the General Ledger report is affected — all other reports pass through unchanged.

---

### Deployment

After pulling changes on production:

```bash
bench restart
```

No `bench migrate` or `bench build` required for Python-only changes.

---

### License

MIT
