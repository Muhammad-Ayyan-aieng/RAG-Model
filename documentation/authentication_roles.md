# Authentication & Roles: Admin vs Public

## Overview

The system has two user roles with different permissions.

**Files responsible:** `src/core/auth.py`, `src/core/limiter.py`

## Role Comparison

| Capability      |   Admin   |      Public       |
|-----------------|-----------|-------------------|
| Upload documents|  Yes      | Yes (with limits) |
| File size limit | Unlimited | 5 MB              |
| File types      | Any       | PDF, TXT only     |
| List documents  |  Yes      | No                |
| Delete documents|  Yes      | No                |
| Ask questions   |  Yes      | Yes               |

## How Role is Detected

Role is determined by the `x-admin-password` HTTP header:

| Header Present |       Value      |        Role       |
|----------------|------------------|-------------------|
| No             | -                | Public            |
| Yes            | Correct password | Admin             |
| Yes            | Wrong password   | 401 Unauthorized  |

**No header = public user.** This is intentional so public users don't need to send anything.

## Authentication Flow
Request arrives
│
▼
Check for x-admin-password header
│
├── No header ──→ Public role
│
├── Wrong password ──→ 401 Unauthorized
│
└── Correct password ──→ Admin role

text

## Admin-Only Endpoints

These endpoints require `require_admin(role)` check:

|        Endpoint        |         Why Admin Only         |
|------------------------|--------------------------------|
| GET /documents/        | See all uploaded documents     |
| DELETE /documents/{id} | Remove documents from database |

## Public Limits (configurable in .env)

|        Limit         | Default  | Admin Override |
|----------------------|----------|----------------|
| Max file size        | 5 MB     | Unlimited      |
| Max files per upload | 3        | Unlimited      |
| Allowed extensions   | pdf, txt | Any            |

## Security Considerations

|      Aspect       |                Implementation             |
|-------------------|-------------------------------------------|
| Password storage  | Plain text in .env (not in code)          |
| Transmission      | HTTPS in production                       |
| Header name       | `x-admin-password` (custom)               |
| Default denial    | All admin endpoints return 403 for public |

## Related Files

|         File          |              Function                |
|-----------------------|--------------------------------------|
| `src/core/auth.py`    | `get_user_role()`, `require_admin()` |
| `src/core/limiter.py` | `validate_upload()`                  |
| `src/api/documents.py`| Uses both for upload/list/delete     |
| `src/api/query.py`    | Uses only role detection (no limits) |