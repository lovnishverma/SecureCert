# 🎓 SecureCert: Blockchain-Based Certificate Verification System

## 📋 Project Overview

**Team Name:** Source Code
**Team Members:**

* Lovnish Verma (Team Leader)
* Aman Choudhary
* Prateek Dhar Dwivedi
* Rahul
* Chandan Saroj

**Hackathon:** Paranox Contest 2.O by TechXNinjas
**Track:** Blockchain & DeFi

---

## 🚀 Problem Statement

In today's digital age, certificate fraud is a growing concern affecting educational institutions, employers, and professionals worldwide. Traditional paper-based certificates are easily forged, and digital certificates stored on centralized servers can be tampered with or lost. Organizations spend considerable time and resources manually verifying credentials, leading to:

* **Certificate Forgery**: Easy manipulation of digital certificates
* **Centralized Vulnerabilities**: Single points of failure in certificate storage
* **Manual Verification**: Time-consuming and error-prone verification processes
* **Trust Issues**: Lack of immutable proof of authenticity

## 💡 Our Solution: SecureCert

SecureCert is a blockchain-powered certificate verification system that ensures **immutable**, **transparent**, and **instantly verifiable** digital certificates. By leveraging the Ethereum blockchain (Sepolia testnet), we create an unchangeable record of certificate authenticity.

### 🌟 Key Features

✅ **Immutable Storage**: Certificate hashes stored on blockchain cannot be altered

✅ **Instant Verification**: Real-time certificate authenticity checks

✅ **Decentralized**: No single point of failure

✅ **Cost-Effective**: Minimal gas fees using efficient hash storage

✅ **User-Friendly**: Simple web interface for issuers and verifiers

✅ **Privacy-Preserving**: Only cryptographic hashes stored on-chain

✅ **MetaMask Integration**: Transactions signed securely by users in-browser

✅ **Transaction Logging**: Issued certificate tx hashes saved locally (`transactions.json`)

---

## 🛠️ Technical Architecture

### Tech Stack

* **Backend**: Python Flask
* **Blockchain**: Ethereum (Sepolia Testnet)
* **Smart Contract**: Solidity
* **Web3 Integration**: Web3.js (frontend) + Web3.py (backend read-only)
* **Cryptography**: SHA-256 Hashing
* **Frontend**: HTML, CSS, JavaScript
* **Storage**: Local file system (`uploads/`, `transactions.json`) → extensible to IPFS/S3

### System Architecture

```
[Certificate File] → [SHA-256 Hash] → [MetaMask Transaction] → [Blockchain Storage] → [Verification]
```

1. **Certificate Issuance**

   * User uploads certificate → Hash computed (SHA-256) in browser
   * Transaction sent through **MetaMask popup** → Stored on blockchain
   * Flask backend logs `{ cert_id: tx_hash }` in `transactions.json`

2. **Verification Process**

   * Upload certificate → Compute SHA-256 hash → Compare with blockchain record

3. **Result**

   * ✅ AUTHENTIC or ❌ INVALID displayed instantly

---

## 📁 Project Structure

```
SecureCert/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── contract/
│   └── CertRegistry.sol        # Smart contract for certificate storage
├── deploy/
│   ├── deploy_contract.py      # Contract deployment script
│   └── deployed_contract.json  # Contract address & ABI
├── transactions.json           # Stores cert_id → tx_hash mappings
├── templates/
│   ├── index.html              # Homepage
│   ├── issue.html              # Certificate issuance page (MetaMask flow)
│   ├── verify.html             # Certificate verification page
│   └── layout.html             # Base template
├── static/
│   └── style.css               # Custom styling
├── uploads/                    # Temporary file storage
└── utils/
    └── crypto_utils.py         # Cryptographic utilities
```

---

## 🚀 Installation & Setup Guide

### Prerequisites

* Python 3.9+
* MetaMask wallet (browser extension)
* Sepolia testnet ETH (from faucets)
* Infura/Alchemy account for RPC access (read-only backend queries)

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd SecureCert
```

### Step 2: Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Fill in your configuration:

```env
# Blockchain Configuration
INFURA_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
ACCOUNT_ADDRESS=0xYourSepoliaWalletAddress
CONTRACT_ADDRESS=0xYourDeployedContract
# PRIVATE_KEY (not needed anymore since MetaMask signs in-browser)

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
```

#### 🔧 Updated Security Improvement:

* **Private Key not required anymore** → All blockchain writes are signed by users in MetaMask.
* Backend only reads blockchain data and logs tx hashes.

### Step 4: Get Test ETH

Get free Sepolia ETH from faucets:

* [Google Cloud Web3 Faucet](https://cloud.google.com/application/web3/faucet/ethereum/sepolia)
* [Alchemy Faucet](https://www.alchemy.com/faucets/ethereum-sepolia)
* [PoW Faucet](https://sepolia-faucet.pk910.de/)

### Step 5: Deploy Smart Contract

```bash
python deploy/deploy_contract.py
```

This creates `deploy/deployed_contract.json` with contract address and ABI.

### Step 6: Run Application

```bash
python app.py
```

Visit `http://127.0.0.1:5000` to use the application!

---

## 📖 How to Use SecureCert

### For Certificate Issuers:

1. Go to **"Issue Certificate"**
2. Enter certificate ID + optional metadata
3. Upload certificate file (PDF/JPG/PNG)
4. Click **"Issue Certificate"** → MetaMask popup opens
5. Confirm transaction → Certificate hash stored on blockchain
6. Transaction hash saved in `transactions.json`

### For Certificate Verifiers:

1. Go to **"Verify Certificate"**
2. Enter Certificate ID + upload file
3. Click **"Verify Certificate"**
4. Instantly see if certificate is ✅ AUTHENTIC or ❌ INVALID

---

## 🔒 Smart Contract Details

### CertRegistry.sol Functions:

```solidity
function setCert(string calldata certificateId, bytes32 digest, string calldata note)
function getCert(string calldata certificateId) returns (bytes32, string memory, bool)
function revokeCert(string calldata certificateId)
```

### Security Features:

* **MetaMask Signing**: Users sign transactions securely in-browser
* **Immutable Records**: Hashes on blockchain cannot be tampered with
* **No Private Key on Server**: Backend does not hold sensitive keys anymore
* **Revocation Support**: Certificates can be revoked if needed

---

## 🔮 Future Enhancements

* [ ] **QR Code Verification** (scan to check authenticity)
* [ ] **Batch Issuance** (issue multiple certs at once)
* [ ] **IPFS/S3 Storage** (decentralized file hosting)
* [ ] **Mobile App** (native Android/iOS)
* [ ] **REST API** (for integration with LMS/HR systems)

---

## ⚠️ Important Notes

* **MetaMask Required**: Certificate issuance now requires MetaMask → users control their own keys
* **Testnet Only**: Uses Sepolia testnet for demo purposes
* **Transactions.json**: Local record of cert_id → tx_hash maintained for easy lookup
* **Security First**: No private keys in backend = safer by design

---

## 👥 Team Contributions

**Lovnish Verma (Team Leader)**

* Project architecture, smart contract development, blockchain integration, MetaMask flow

**Aman Choudhary**

* Flask backend, frontend UI/UX, file handling, transaction logging

**Prateek Dhar Dwivedi**

* Contract deployment, environment setup, debugging & QA

**Rahul**

* Contract deployment, environment setup, debugging & QA

**Chandan Saroj**

* Contract deployment, environment setup, debugging & QA

---

**“Building the future of digital trust, one certificate at a time.” 🚀**

