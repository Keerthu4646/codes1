import json
import os

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "records")
os.makedirs(_DIR, exist_ok=True)

def save_record(record, dict):
    path = os.path.join(_DIR, f"{record['invoice_number']}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, default=str)

def get_record(invoice_id:str):
    path = os.path.join(_DIR, f"{invoice_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def list_records():
    out = []
    for name in os.listdir(_DIR):
        if name.endswith('.json'):
            with open(os.path.join(_DIR, name), 'r', encoding='utf-8') as f:
                out.append(json.load(f))
    return out
