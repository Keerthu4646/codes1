import json
import os
from flask import Flask, jsonify

from common.logging_setup import get_logger

app = Flask(__name__)
log = get_logger("supplier_service")

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "suppliers.json")
with open(PATH, encoding='utf-8') as f:
    suppliers = json.load(f)
@app.get('/health')
def health():
    return jsonify({"status": "ok"})

@app.get("/suppliers/<gstin>")
def get_supplier(gstin):
    log.info("supplier lookup gstin=%s", gstin)
    supplier = suppliers.get(gstin.upper())
    if supplier is None:
        return jsonify({"error": "supplier not found", "message": f"NO supplier for GSTIN: {gstin}"}), 404
    return jsonify({"gstin": gstin.upper(), **supplier})


@app.route('/suppliers', methods=['GET'])
def get_suppliers():
    return jsonify(list(suppliers.values()))

if __name__ == '__main__':
    app.run(debug=True)