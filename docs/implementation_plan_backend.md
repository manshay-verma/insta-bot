# Implementation Plan: Backend - Account Module

## Overview
This plan outlines the initialization of the Django backend and the development of the `account` module, which is responsible for managing Instagram bot credentials, session cookies, and account health.

---

## 🏗️ 1. Project Initialization

### 1.1 Setup Django Project
- Initialize Django in the `backend/` directory.
- Rename the main configuration folder to `config`.
- Configure `settings.py` for:
    - PostgreSQL connection details.
    - Django REST Framework (DRF) integration.
    - JWT Authentication setup.

### 1.2 Convert Folders to Apps
- Initialize the following as Django Apps:
    - `account`
    - `api`
    - `analytics`
    - `downloads`

---

## 🛡️ 2. Account Module Development (`backend/account/`)

### 2.1 Database Models (PostgreSQL)
Implement `BotAccount` model with:
- `username`: Instagram username (Unique).
- `password_encrypted`: Encrypted credentials.
- `status`: Choice field (active, paused, banned, checkpoint).
- `trust_score`: Decimal (0.0 to 1.0).
- `cookies_json`: JSONField for session persistence.
- `proxy`: Reference to proxy settings.
- `last_login`: Timestamp.

### 2.2 Security & Encryption
- Implement a utility for encrypting/decrypting sensitive bot credentials before storing them in the database.

### 2.3 Serializers & API Views
- Create DRF Serializers for account data.
- Implement API endpoints:
    - `GET /api/v1/accounts/`: List all accounts.
    - `POST /api/v1/accounts/`: Add a new bot account.
    - `GET /api/v1/accounts/{id}/health/`: Get health metrics.

---

## 🔄 3. Integration with Automation Layer

### 3.1 Cookie Sync
- Logic to sync `cookies_json` from the database to the `playwright` module's cookie loading system.

### 3.2 Health Check Integration
- Automated task to verify session validity using `InstagramBrowser.is_session_valid()` and update the database status.

---

## 📅 4. Implementation Steps

1. **Phase 1**: Django project setup and `account` app initialization.
2. **Phase 2**: Define `BotAccount` model & run migrations.
3. **Phase 3**: Build Encryption utility.
4. **Phase 4**: Setup Serializers and basic CRUD endpoints.
5. **Phase 5**: Documentation update.

---

## ✅ Verification Plan
- Unit tests for Model creation.
- API testing via Postman/cURL for account management.
- Verify encryption/decryption cycle.
