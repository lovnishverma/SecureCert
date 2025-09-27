import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from web3 import Web3
from pathlib import Path
from cert_utils import compute_sha256_hex, sha256_hex_to_bytes32
import json
import time
from datetime import datetime

# --- Setup ---
BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

UPLOAD_FOLDER = BASE / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

TRANSACTIONS_FILE = BASE / "transactions.json"

# --- Web3 Setup ---
INFURA_URL = os.getenv("INFURA_URL")
ACCOUNT = os.getenv("ACCOUNT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

if not INFURA_URL:
    raise SystemExit("Please set INFURA_URL in .env")
if not ACCOUNT or not PRIVATE_KEY:
    raise SystemExit("Set ACCOUNT_ADDRESS and PRIVATE_KEY in .env")

w3 = Web3(Web3.HTTPProvider(INFURA_URL))
acct = w3.to_checksum_address(ACCOUNT)
chain_id = 11155111  # Sepolia

# Load ABI + contract address from deploy output
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
    raise SystemExit(
        "deploy/deployed_contract.json not found. Run deploy/deploy_contract.py first.")

contract = w3.eth.contract(
    address=w3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI)


# --- Jinja2 filter ---
@app.template_filter('timestamp_format')
def timestamp_format(ts):
    """Convert Unix timestamp to human-readable string"""
    if ts is None or ts == 0:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime("%B %d, %Y, %I:%M:%S %p")


# --- Transaction management ---
def load_transactions():
    if TRANSACTIONS_FILE.exists():
        try:
            with open(TRANSACTIONS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
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


@app.route("/issue", methods=["GET", "POST"])
def issue():
    if request.method == "POST":
        cert_id = request.form.get("cert_id", "").strip()
        file = request.files.get("file")
        txid_note = request.form.get("txid_note", "").strip()

        if not cert_id or not file:
            flash("❌ Provide certificate ID and file", "danger")
            return redirect(url_for("issue"))

        # Check if certificate already exists
        try:
            existing = contract.functions.getCert(cert_id).call()
            if existing[1] > 0:
                flash(
                    f"❌ Certificate ID '{cert_id}' already exists!", "danger")
                return redirect(url_for("issue"))
        except Exception:
            pass

        # Save uploaded file
        filename = f"{int(time.time())}_{file.filename}"
        save_path = UPLOAD_FOLDER / filename
        file.save(save_path)

        # Compute hash
        sha_hex = compute_sha256_hex(save_path)
        digest_bytes = sha256_hex_to_bytes32(sha_hex)

        try:
            # Build & send transaction
            nonce = w3.eth.get_transaction_count(acct)
            txn = contract.functions.setCert(cert_id, digest_bytes, txid_note).build_transaction({
                "from": acct,
                "nonce": nonce,
                "gas": 300000,
                "gasPrice": w3.to_wei("20", "gwei")
            })

            signed = w3.eth.account.sign_transaction(
                txn, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash_hex = w3.to_hex(tx_hash)

            # Wait for confirmation
            print(f"Transaction sent: {tx_hash_hex}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt.status == 1:
                save_transaction(cert_id, tx_hash_hex)
                flash(
                    f"✅ Certificate issued successfully! Transaction: {tx_hash_hex}", "success")
            else:
                flash("❌ Transaction failed! Please try again.", "danger")

        except Exception as e:
            flash(f"❌ Error issuing certificate: {str(e)}", "danger")

        finally:
            # Clean up uploaded file
            try:
                os.unlink(save_path)
            except:
                pass

        return redirect(url_for("issue"))

    return render_template("issue.html")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        cert_id = request.form.get("cert_id", "").strip()
        file = request.files.get("file")

        if not cert_id or not file:
            flash("❌ Provide certificate ID and file", "danger")
            return redirect(url_for("verify"))

        filename = f"{int(time.time())}_{file.filename}"
        save_path = UPLOAD_FOLDER / filename
        file.save(save_path)
        uploaded_hash = compute_sha256_hex(save_path)

        # Clean up immediately
        try:
            os.unlink(save_path)
        except:
            pass

        # Read on-chain certificate
        try:
            onchain = contract.functions.getCert(cert_id).call()
            onchain_digest = onchain[0]
            timestamp = onchain[1]
            revoked = onchain[2]
            txid = onchain[3]

            if timestamp == 0:
                flash("❌ Certificate ID not found", "danger")
                return render_template("verify.html",
                                       result=True,
                                       match=False,
                                       uploaded_hash=uploaded_hash,
                                       onchain_hash="Certificate not found",
                                       revoked=False,
                                       timestamp=0,
                                       txid="",
                                       cert_id=cert_id,
                                       tx_hash=None)

            onchain_digest_hex = w3.to_hex(onchain_digest)
            onchain_hex = onchain_digest_hex[2:] if onchain_digest_hex.startswith(
                "0x") else onchain_digest_hex

        except Exception as e:
            flash(f"❌ Failed to read blockchain data: {e}", "danger")
            return redirect(url_for("verify"))

        # Compare hashes
        match = (uploaded_hash.lower() == onchain_hex.lower())
        tx_hash = get_transaction_hash(cert_id)

        # Try fetching from events if not in our records
        if not tx_hash:
            try:
                cert_filter = contract.events.CertSet.create_filter(
                    fromBlock=0,
                    argument_filters={'certificateId': cert_id}
                )
                events = cert_filter.get_all_entries()
                if events:
                    tx_hash = events[-1]['transactionHash'].hex()
                    save_transaction(cert_id, tx_hash)
            except Exception as e:
                print(f"Could not retrieve transaction hash from events: {e}")

        return render_template("verify.html",
                               result=True,
                               match=match,
                               uploaded_hash=uploaded_hash,
                               onchain_hash=onchain_hex,
                               revoked=revoked,
                               timestamp=timestamp,
                               txid=txid,
                               cert_id=cert_id,
                               tx_hash=tx_hash)

    return render_template("verify.html", result=False)


@app.route("/contract_info")
def contract_info():
    try:
        owner = contract.functions.owner().call()
        return f"""
        <h2>Contract Information</h2>
        <p><strong>Contract Address:</strong> {CONTRACT_ADDRESS}</p>
        <p><strong>Owner:</strong> {owner}</p>
        <p><strong>Your Account:</strong> {acct}</p>
        <p><strong>Chain ID:</strong> {chain_id}</p>
        <p><strong>Network:</strong> Sepolia Testnet</p>
        <p><a href="https://sepolia.etherscan.io/address/{CONTRACT_ADDRESS}" target="_blank">View on Etherscan</a></p>
        <p><a href="{url_for('index')}">Back to Home</a></p>
        """
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    # Ensure transactions file exists
    if not TRANSACTIONS_FILE.exists():
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump({}, f)

    app.run(debug=True, port=5000)
