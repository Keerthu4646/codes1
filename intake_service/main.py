import json
import uuid
from datetime import datetime, timedelta, timezone
 
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
 
from common.azure_clients import blob_service, init_storage, queue_client
from common.config import CONFIG
from common.logging_setup import get_logger, log_step
from common.store import get_record, list_records, save_record
 
app = FastAPI(title="CartNova Intake Service")
log = get_logger("intake")
 
MAX_BYTES = CONFIG["limits"]["max_file_mb"] * 1024 * 1024
ALLOWED = CONFIG["limits"]["allowed_types"]
RAW = CONFIG["blob"]["raw_container"]
 
 
@app.on_event("startup")
def startup():
    init_storage()
 
 
# ---- one consistent error format, no stack traces ----
def _err(status, code, message):
    return JSONResponse(status_code=status,
                        content={"error": code, "message": message})
 
 
@app.exception_handler(StarletteHTTPException)
async def http_err(request, exc):
    return _err(exc.status_code, "http_error", str(exc.detail))
 
 
@app.exception_handler(RequestValidationError)
async def validation_err(request, exc):
    return _err(422, "validation_error", "Invalid request data")
 
 
@app.exception_handler(Exception)
async def unhandled(request, exc):
    log.exception("unhandled error")
    return _err(500, "internal_error", "Something went wrong")
 
 
@app.middleware("http")
async def log_requests(request, call_next):
    log.info("request %s %s", request.method, request.url.path)
    return await call_next(request)
 
 
# ---- POST /invoices ----
@app.post("/invoices", status_code=202)
async def upload_invoice(file: UploadFile = File(...),
                         supplier_gstin: str = Form(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, "Only PDF, JPG or PNG files are allowed")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 5 MB")
    if len(supplier_gstin.strip()) != 15:
        raise HTTPException(422, "supplier_gstin must be 15 characters")
 
    invoice_id = "inv_" + uuid.uuid4().hex[:6]
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    blob_name = f"{invoice_id}.{ext}"
 
    blob_service().get_blob_client(RAW, blob_name).upload_blob(data, overwrite=True)
    log_step(log, invoice_id, "blob_uploaded", blob=blob_name)
 
    save_record({
        "invoice_id": invoice_id,
        "status": "RECEIVED",
        "supplier_gstin": supplier_gstin.strip().upper(),
        "blob_name": blob_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fields": None,
        "reasons": [],
    })
 
    queue_client().send_message(json.dumps(
        {"invoice_id": invoice_id, "blob_name": blob_name,
         "supplier_gstin": supplier_gstin.strip().upper()}))
    log_step(log, invoice_id, "queued")
 
    return {"invoice_id": invoice_id, "status": "RECEIVED"}
 
 
# ---- helper: 15-minute read-only SAS link ----
def _sas_url(blob_name):
    bs = blob_service()
    token = generate_blob_sas(
        account_name=bs.account_name,
        container_name=RAW,
        blob_name=blob_name,
        account_key=bs.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc)
        + timedelta(minutes=CONFIG["sas_expiry_minutes"]),
    )
    return f"{bs.url}{RAW}/{blob_name}?{token}"
 
 
# ---- GET /invoices/{id} ----
@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    rec = get_record(invoice_id)
    if rec is None:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    rec["document_url"] = _sas_url(rec["blob_name"])
    return rec
 
 
# ---- GET /invoices (filters + pagination) ----
@app.get("/invoices")
def list_invoices(status: str | None = None,
                  supplier: str | None = None,
                  page: int = Query(1, ge=1),
                  size: int = Query(10, ge=1, le=50)):
    items = list_records()
    if status:
        items = [i for i in items if i["status"] == status.upper()]
    if supplier:
        items = [i for i in items if i["supplier_gstin"] == supplier.upper()]
    items.sort(key=lambda i: i["created_at"], reverse=True)
    start = (page - 1) * size
    return {"total": len(items), "page": page, "size": size,
            "items": items[start:start + size]}
