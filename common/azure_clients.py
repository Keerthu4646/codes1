from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
import common
from common.config import env, CONFIG 
 
def blob_service():
    return BlobServiceClient.from_connection_string(common.config.env("STORAGE_CONNECTION_STRING"))
 
 
def queue_client():
    return QueueClient.from_connection_string(
        common.config.env("STORAGE_CONNECTION_STRING"), common.config.CONFIG["queue"]["name"]
    )
 
 
def init_storage():
    bs = blob_service()
    for name in (CONFIG["blob"]["raw_container"], CONFIG["blob"]["reports_container"]):
        try:
            bs.create_container(name)
        except Exception:
            pass
    try:
        queue_client().create_queue()
    except Exception:
        pass
