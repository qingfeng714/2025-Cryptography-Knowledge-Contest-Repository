from flask import Flask, request, jsonify
from services.ingest_service import parseDICOM
from services.ner_service import detectPHI
from services.crypto_processor import protectData
from services.audit_service import logAction

app = Flask(__name__)

@app.route("/api/ingest", methods=["POST"])
def ingest():
    text = request.form.get("text", "")
    dicom_file = request.files.get("dicom")
    ingest_id = parseDICOM(dicom_file)
    entities = detectPHI(text)
    logAction(ingest_id, "ingest", "system")
    return jsonify({"ingest_id": ingest_id, "entities": entities, "status": "ok"})

@app.route("/api/protect", methods=["POST"])
def protect():
    data = request.json
    ingest_id = data.get("ingest_id")
    policy = data.get("policy", {})
    protected = protectData(ingest_id, policy)
    logAction(protected["artifact_id"], "protect", "system")
    return jsonify(protected)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
