# app.py
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from web3 import Web3
from pathlib import Path
from cert_utils import compute_sha256_hex, sha256_hex_to_bytes32
import json
import time

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")
UPLOAD_FOLDER = BASE / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

INFURA_URL = os.getenv("INFURA_URL")
ACCOUNT = os.getenv("ACCOUNT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
# optional, or use deployed_contract.json
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

if not INFURA_URL:
    raise SystemExit("Please set INFURA_URL in .env")
if not ACCOUNT or not PRIVATE_KEY:
    raise SystemExit("Set ACCOUNT_ADDRESS and PRIVATE_KEY in .env")

w3 = Web3(Web3.HTTPProvider(INFURA_URL))
acct = w3.to_checksum_address(ACCOUNT)
chain_id = 11155111  # Sepolia

# load ABI + contract address from deploy output if present
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
    # user must provide ABI: for simplicity, we load ABI from the compiled contract shipped here
    # you can paste ABI manually here if required.
    # For now, we will try to read the contract source ABI file path (not included). Raise helpful error:
    raise SystemExit(
        "deploy/deployed_contract.json not found. Run deploy/deploy_contract.py first to compile+deploy.")

contract = w3.eth.contract(
    address=w3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/issue", methods=["GET", "POST"])
def issue():
    if request.method == "POST":
        cert_id = request.form.get("cert_id", "").strip()
        file = request.files.get("file")
        txid_note = request.form.get("txid_note", "").strip()
        if not cert_id or not file:
            flash("Provide certificate id and file", "danger")
            return redirect(url_for("issue"))
        filename = f"{int(time.time())}_{file.filename}"
        save_path = UPLOAD_FOLDER / filename
        file.save(save_path)

        # compute hash
        sha_hex = compute_sha256_hex(save_path)
        # convert to bytes32
        digest_bytes = sha256_hex_to_bytes32(sha_hex)

        # build & send transaction to call setCert(cert_id, bytes32 digest, string txid)
        nonce = w3.eth.get_transaction_count(acct)
        txn = contract.functions.setCert(cert_id, digest_bytes, txid_note).build_transaction({
            "from": acct,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": w3.to_wei("20", "gwei")
        })
        signed = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = w3.to_hex(tx_hash)
        flash(
            f"Issued certificate and wrote hash on-chain. Tx: {tx_hash_hex}", "success")
        return redirect(url_for("index"))

    return render_template("issue.html")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        cert_id = request.form.get("cert_id", "").strip()
        file = request.files.get("file")
        if not cert_id or not file:
            flash("Provide certificate id and file", "danger")
            return redirect(url_for("verify"))
        filename = f"{int(time.time())}_{file.filename}"
        save_path = UPLOAD_FOLDER / filename
        file.save(save_path)

        uploaded_hash = compute_sha256_hex(save_path)

        # read on-chain cert
        try:
            onchain = contract.functions.getCert(cert_id).call()
            # onchain is (bytes32 digest, uint256 timestamp, bool revoked, string txid)
            onchain_digest = onchain[0]  # bytes32
            onchain_digest_hex = w3.to_hex(onchain_digest)  # 0x...
            revoked = onchain[2]
            timestamp = onchain[1]
            txid = onchain[3]
        except Exception as e:
            flash(f"Failed to read on-chain data: {e}", "danger")
            return redirect(url_for("verify"))

        # compare: onchain_digest_hex is 0x + 64 hex chars representing the raw bytes saved.
        # But our uploaded_hash is SHA-256 hex string (no 0x). We can compare by converting bytes to hex.
        # Convert onchain 0x... to hex without 0x and compare
        if onchain_digest_hex.startswith("0x"):
            onchain_hex = onchain_digest_hex[2:]
        else:
            onchain_hex = onchain_digest_hex

        match = (uploaded_hash.lower() == onchain_hex.lower())

        return render_template("verify.html", result=True, match=match,
                               uploaded_hash=uploaded_hash, onchain_hash=onchain_hex,
                               revoked=revoked, timestamp=timestamp, txid=txid, cert_id=cert_id)

    return render_template("verify.html", result=False)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
