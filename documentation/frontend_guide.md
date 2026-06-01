# Frontend Guide: User Interface

## Overview

Two HTML pages provide the user interface.

**Files responsible:** `frontend/index.html`, `frontend/admin.html`

## Page 1: Public Chat (index.html)

**Purpose:** Document upload and question answering for all users.

**Features:**
- Drag-and-drop file upload
- Question input with Enter key support
- Real-time answer display with source citations
- Upload status messages (success, error, loading)

**API Calls Made:**
|     Action     |       Endpoint      | Method |
|----------------|---------------------|--------|
| Upload file    | `/documents/upload` | POST   |
| Ask question   | `/query/ask`        | POST   |

**User Flow:**
1. Select/upload a document
2. Type a question
3. View answer with source documents
4. Upload another document (cumulative knowledge base)

## Page 2: Admin Panel (admin.html)

**Purpose:** Document management for administrators.

**Features:**
- Password-protected entry
- Unlimited document upload (no size/type limits)
- List all documents with metadata
- Delete documents with confirmation
- System statistics (document count, chunk count)

**API Calls Made:**
|     Action     |       Endpoint        | Method | Auth Required    |
|----------------|-----------------------|--------|------------------|
| Verify password| GET /documents/       | GET    | x-admin-password |
| Upload document| POST /documents/upload| POST   | x-admin-password |
| List documents | GET /documents/       | GET    | x-admin-password |
| Delete document| DELETE /documents/{id}| DELETE | x-admin-password |

**Password Flow:**
1. Page loads → shows password modal
2. User enters password → system verifies via GET /documents/
3. If correct → show admin interface
4. If wrong → show error, stay in modal

## API Base URL Configuration

Both pages use a configurable `API_BASE` variable:

```javascript
const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://your-backend.onrender.com';
This allows the same code to work locally and in production.

Common Elements
Status Messages:

Loading (blue): "Processing..."

Success (green): "✓ Document uploaded"

Error (red): "✗ Upload failed"

File Validation (Public Page):

Max size: 5 MB

Formats: PDF, TXT

Single file per upload

Related Files
File	Purpose
frontend/index.html	Public interface
frontend/admin.html	Admin management
src/main.py	Serves static files
src/api/documents.py	Backend endpoints
src/api/query.py	Question endpoint