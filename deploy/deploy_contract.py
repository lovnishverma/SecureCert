# deploy/deploy_contract.py
import os
from pathlib import Path
from dotenv import load_dotenv
from solcx import compile_standard, install_solc
from web3 import Web3
import json

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / '.env')

INFURA_URL = os.getenv("INFURA_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT = os.getenv("ACCOUNT_ADDRESS")

if not INFURA_URL or not PRIVATE_KEY or not ACCOUNT:
    raise SystemExit("Set INFURA_URL, PRIVATE_KEY and ACCOUNT_ADDRESS in .env")

# install a compatible solc version if not present
install_solc('0.8.17')

# read solidity
contract_path = Path(BASE / "contract" / "CertRegistry.sol")
source = contract_path.read_text()

compiled = compile_standard({
    "language": "Solidity",
    "sources": {"CertRegistry.sol": {"content": source}},
    "settings": {
        "outputSelection": {
            "*": {
                "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
            }
        }
    }
}, solc_version="0.8.17")

bytecode = compiled['contracts']['CertRegistry.sol']['CertRegistry']['evm']['bytecode']['object']
abi = compiled['contracts']['CertRegistry.sol']['CertRegistry']['abi']

# connect to web3
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
chain_id = 11155111  # Sepolia chain id
acct = w3.to_checksum_address(ACCOUNT)

# build tx
Cert = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(acct)

transaction = Cert.constructor().build_transaction({
    'chainId': chain_id,
    'from': acct,
    'nonce': nonce,
    'gas': 4000000,
    'gasPrice': w3.to_wei('30', 'gwei'),
})

signed_txn = w3.eth.account.sign_transaction(
    transaction, private_key=PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
print("Deploy tx sent. Tx hash:", w3.to_hex(tx_hash))
print("Waiting for receipt...")
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print("Contract deployed at address:", tx_receipt.contractAddress)

# output ABI + address to file for easy use
out = BASE / "deploy" / "deployed_contract.json"
out.write_text(json.dumps({
    "address": tx_receipt.contractAddress,
    "abi": abi
}, indent=2))
print(f"Wrote ABI+address to {out}")
