import json, os, time
import requests
from pydantic import ValidationError
from common.azure_clients import blob_service, queue_client, init_storage
from common.config import CONFIG
from common.logging_setup import get_logger, log_step
from common.schemas import Invoice
from common.store import get_record, save_record
 
log = get_logger("worker")
SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_invoices")
 
def extract(gstin):
    """OCR stand-in: reads fields from sample_invoices/<gstin>.json.
    Replace with Azure Document Intelligence in production."""
    p = os.path.join(SAMPLES, f"{gstin}.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)
 
def check_supplier(gstin):
    try:
        r = requests.get(f"{CONFIG['supplier_service']['url']}/suppliers/{gstin}",
                         timeout=CONFIG["supplier_service"]["timeout_seconds"])
    except requests.RequestException:
        return "DOWN", None
    if r.status_code == 404:
        return "UNKNOWN", None
    return "OK", r.json()
 
def process(msg):
    inv_id, gstin = msg["invoice_id"], msg["supplier_gstin"]
    rec = get_record(inv_id)
    log_step(log, inv_id, "processing")
    blob_service().get_blob_client(CONFIG["blob"]["raw_container"], msg["blob_name"]).download_blob().readall()
    reasons, status = [], "APPROVED"
    fields = extract(gstin)
    if fields is None:
        status = "NEEDS_REVIEW"
        reasons.append("OCR could not read invoice fields")
    else:
        try:
            Invoice(**fields)
        except ValidationError as e:
            status = "NEEDS_REVIEW"
            reasons += [x["msg"] for x in e.errors()]
    state, sup = check_supplier(gstin)
    if state == "DOWN":
        status = "PENDING_SUPPLIER_CHECK"
        reasons.append("supplier service unavailable")
        log.warning("invoice=%s supplier service down", inv_id)
    elif state == "UNKNOWN":
        status = "REJECTED"
        reasons.append("unknown supplier")
    elif not sup.get("active"):
        status = "REJECTED"
        reasons.append("supplier is inactive")
    rec.update(status=status, reasons=reasons, fields=fields)
    save_record(rec)
    log_step(log, inv_id, "done", status=status)
 
def main(once=False):
    init_storage()
    q = queue_client()
    while True:
        got = False
        for m in q.receive_messages(visibility_timeout=5):
            got = True
            msg = json.loads(m.content)
            try:
                if m.dequeue_count > CONFIG["queue"]["max_retries"]:
                    rec = get_record(msg["invoice_id"])
                    rec["status"] = "FAILED"
                    save_record(rec)
                    q.delete_message(m)
                    continue
                process(msg)
                q.delete_message(m)
            except Exception:
                log.exception("failed invoice=%s attempt=%s", msg["invoice_id"], m.dequeue_count)
        if once and not got:
            break
        time.sleep(2)
 
if __name__ == "__main__":
    main()
 