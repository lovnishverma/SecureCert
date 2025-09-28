import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from cert_utils import compute_sha256_hex

# --- Setup ---
BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

UPLOAD_FOLDER = BASE / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

TRANSACTIONS_FILE = BASE / "transactions.json"

# --- Load Contract ABI + Address ---
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
deployed_file = BASE / "deploy" / "deployed_contract.json"
if deployed_file.exists():
    with open(deployed_file) as f:
        data = json.load(f)
        CONTRACT_ADDRESS = data.get("address")
        ABI = data.get("abi")
else:
    if not CONTRACT_ADDRESS:
        raise SystemExit(
            "Contract address not set. Deploy contract or set CONTRACT_ADDRESS in .env")

# --- Jinja2 filter ---


@app.template_filter('timestamp_format')
def timestamp_format(ts):
    if ts is None or ts == 0:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime("%B %d, %Y, %I:%M:%S %p")

# --- Transaction management ---


def load_transactions():
    if TRANSACTIONS_FILE.exists():
        try:
            with open(TRANSACTIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_transaction(cert_id, tx_hash):
    transactions = load_transactions()
    transactions[cert_id] = tx_hash
    try:
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump(transactions, f, indent=2)
    except Exception as e:
        print(f"Error saving transaction: {e}")


def get_transaction_hash(cert_id):
    transactions = load_transactions()
    return transactions.get(cert_id)

# --- Routes ---


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/issue", methods=["GET"])
def issue():
    """Render Issue Certificate page"""
    return render_template("issue.html",
                           CONTRACT_ADDRESS=CONTRACT_ADDRESS,
                           ABI=json.dumps(ABI))


@app.route("/upload_hash", methods=["POST"])
def upload_hash():
    """
    Endpoint to compute SHA-256 hash of uploaded certificate.
    Frontend will use this hash with MetaMask to sign and write to blockchain.
    """
    file = request.files.get("file")
    cert_id = request.form.get("cert_id", "").strip()
    if not file or not cert_id:
        return jsonify({"error": "Certificate ID and file are required"}), 400

    # Save file temporarily
    filename = f"{int(time.time())}_{file.filename}"
    save_path = UPLOAD_FOLDER / filename
    file.save(save_path)

    # Compute SHA-256
    sha_hex = compute_sha256_hex(save_path)

    # Clean up file
    try:
        os.unlink(save_path)
    except:
        pass

    return jsonify({"cert_id": cert_id, "sha256": sha_hex})


@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        cert_id = request.form.get("cert_id", "").strip()
        file = request.files.get("file")
        if not cert_id or not file:
            flash("❌ Provide certificate ID and file", "danger")
            return redirect(url_for("verify"))

        # Save file temporarily
        filename = f"{int(time.time())}_{file.filename}"
        save_path = UPLOAD_FOLDER / filename
        file.save(save_path)
        uploaded_hash = compute_sha256_hex(save_path)

        try:
            from web3 import Web3
            INFURA_URL = os.getenv("INFURA_URL")
            w3 = Web3(Web3.HTTPProvider(INFURA_URL))
            contract = w3.eth.contract(
                address=w3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI)
            onchain = contract.functions.getCert(cert_id).call()
            onchain_digest = onchain[0]
            timestamp = onchain[1]
            revoked = onchain[2]
            txid = onchain[3]

            onchain_digest_hex = w3.to_hex(onchain_digest)[
                2:] if onchain_digest else ""
        except Exception as e:
            flash(f"❌ Failed to read blockchain data: {e}", "danger")
            return redirect(url_for("verify"))

        match = (uploaded_hash.lower() == onchain_digest_hex.lower())
        tx_hash = get_transaction_hash(cert_id)

        return render_template("verify.html",
                               result=True,
                               match=match,
                               uploaded_hash=uploaded_hash,
                               onchain_hash=onchain_digest_hex,
                               revoked=revoked,
                               timestamp=timestamp,
                               txid=txid,
                               cert_id=cert_id,
                               tx_hash=tx_hash)

    return render_template("verify.html", result=False)


@app.route("/save_tx", methods=["POST"])
def save_tx():
    data = request.get_json()
    cert_id = data.get("cert_id")
    tx_hash = data.get("tx_hash")
    if not cert_id or not tx_hash:
        return jsonify({"error": "cert_id and tx_hash are required"}), 400
    save_transaction(cert_id, tx_hash)
    return jsonify({"success": True})


@app.route("/contract_info")
def contract_info():
    return render_template('contract_info.html', CONTRACT_ADDRESS=CONTRACT_ADDRESS)


@app.route("/help")
def help():
    return render_template('help.html')


# --- Main ---
if __name__ == "__main__":
    if not TRANSACTIONS_FILE.exists():
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump({}, f)

    app.run(debug=True, port=5000)
