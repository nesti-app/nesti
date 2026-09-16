# Home Inventory — Architecture

## 1. Overview

Nesti is a server-rendered web application with progressive enhancement.

The backend is a Python FastAPI application. The frontend uses Jinja2 templates with HTMX for interactivity, Tailwind CSS for styling, and minimal vanilla JavaScript for browser-only features (camera, QR scanning, image preview, PWA).

The application is designed to be deployed as a serverless function on Vercel, or as a Docker container, with external PostgreSQL (or SQLite) and external object storage (S3-compatible). No local filesystem state is assumed in production.

---

## 2. Project Structure

```text
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application factory
│   ├── config.py            # Settings / environment variables
│   ├── dependencies.py      # Shared FastAPI dependencies
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py        # SQLAlchemy async engine / session
│   │   └── base.py          # Declarative base
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── service.py       # Authentication abstraction
│   │   ├── middleware.py    # Session / auth middleware
│   │   └── routes.py       # Login / logout routes
│   │
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── routes.py
│   │
│   ├── access/
│   │   ├── __init__.py
│   │   ├── models.py        # Access Scope, Scope Rules, Scope Permissions
│   │   ├── schemas.py
│   │   ├── service.py       # Authorization engine
│   │   └── routes.py
│   │
│   ├── items/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── routes.py
│   │
│   ├── categories/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── routes.py
│   │
│   ├── tags/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── routes.py
│   │
│   ├── locations/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── routes.py
│   │
│   ├── movements/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── routes.py
│   │
│   ├── relationships/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── routes.py
│   │
│   ├── media/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py       # Image processing, upload, storage
│   │   └── routes.py
│   │
│   ├── qr/
│   │   ├── __init__.py
│   │   ├── service.py       # QR generation
│   │   └── routes.py
│   │
│   ├── labels/
│   │   ├── __init__.py
│   │   ├── service.py       # Label layout / PNG generation
│   │   └── routes.py
│   │
│   ├── search/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   └── routes.py
│   │
│   ├── backup/
│   │   ├── __init__.py
│   │   ├── service.py       # Export / import logic
│   │   └── routes.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── items.py
│   │       ├── search.py
│   │       ├── categories.py
│   │       ├── tags.py
│   │       └── locations.py
│   │
│   └── common/
│       ├── __init__.py
│       ├── exceptions.py
│       └── pagination.py
│
├── templates/
│   ├── base.html
│   ├── components/
│   ├── auth/
│   ├── items/
│   ├── categories/
│   ├── tags/
│   ├── locations/
│   ├── access/
│   ├── users/
│   ├── dashboard/
│   ├── labels/
│   ├── search/
│   └── backup/
│
├── static/
│   ├── css/
│   ├── js/
│   ├── icons/
│   └── manifest.json
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/
│
├── Dockerfile
├── compose.yaml
├── vercel.json
├── pyproject.toml
├── alembic.ini
├── .env.example
├── .gitignore
├── README.md
├── ARCHITECTURE.md
└── SPECIFICATION.md
```

---

## 3. Technology Stack

### Backend

| Component        | Technology              |
|------------------|-------------------------|
| Language         | Python 3.13+            |
| Framework        | FastAPI                 |
| Validation       | Pydantic v2             |
| ORM              | SQLAlchemy 2.x (async)  |
| Migrations       | Alembic                 |
| Database         | PostgreSQL or SQLite    |
| Templating       | Jinja2                  |
| Auth             | Local (argon2 + JWT)    |
| Object storage   | S3-compatible           |

### Frontend

| Component     | Technology                    |
|---------------|-------------------------------|
| HTML          | Jinja2 server-rendered        |
| Interactivity | HTMX                          |
| CSS           | Tailwind CSS                  |
| JavaScript    | Vanilla (minimal, progressive)|
| QR scanning   | jsQR or html5-qrcode library  |
| QR generation | Server-side (Python qrcode)   |

---

## 4. Permission Matrix

### Roles

| Permission             | Admin | Editor | Viewer |
|------------------------|:-----:|:------:|:------:|
| Manage users           | ✅    | ❌     | ❌     |
| Manage access scopes   | ✅    | ❌     | ❌     |
| Manage categories      | ✅    | ❌     | ❌     |
| Manage tags            | ✅    | ❌     | ❌     |
| Manage locations       | ✅    | ❌     | ❌     |
| Manage app settings    | ✅    | ❌     | ❌     |
| Import / Export        | ✅    | ❌     | ❌     |
| Create items           | ✅*   | ✅*    | ❌     |
| Edit items             | ✅*   | ✅*    | ❌     |
| Delete items           | ✅*   | ❌     | ❌     |
| Move items             | ✅*   | ✅*    | ❌     |
| Upload images          | ✅*   | ✅*    | ❌     |
| Manage item relations  | ✅*   | ✅*    | ❌     |
| View items             | ✅*   | ✅*    | ✅*    |
| Search items           | ✅*   | ✅*    | ✅*    |
| Scan QR codes          | ✅    | ✅    | ✅    |
| View movement history  | ✅*   | ✅*    | ✅*    |
| View item details      | ✅*   | ✅*    | ✅*    |

\* Subject to Access Scope rules. Even admins are limited by scopes unless a global admin scope or bypass is configured.

---

## 5. Access Scope System

### Design

Access Scopes are the primary authorization mechanism. They decouple permissions from the physical organization of items.

An Access Scope contains:

- **Rules** — filters that define which items the scope covers
- **Permissions** — what actions are allowed on matched items
- **Users** — who receives these permissions

### Rule Types

| Rule Type       | Description                        |
|-----------------|------------------------------------|
| `location`      | Match items at a specific location |
| `category`      | Match items in a specific category |
| `tag`           | Match items with a specific tag    |
| `specific_item` | Match exact items by UUID          |

### Rule Combination

Rules within one Access Scope are combined using **AND** semantics.

Example:

```
location = Garage AND category = Tools
```

Matches only items that are **both** in the Garage **and** in the Tools category.

### Permission Types

| Permission      | Description                    |
|-----------------|--------------------------------|
| `view`          | Can see the item               |
| `create`        | Can create items in this scope |
| `edit`          | Can modify the item            |
| `move`          | Can change item location       |
| `delete`        | Can delete the item            |
| `manage_images` | Can upload/modify images       |

### Evaluation Flow

```
Request for item X
       ↓
Identify user
       ↓
Load user's access scopes
       ↓
For each scope:
  Does item X match all rules?
       ↓
  If yes: collect granted permissions
       ↓
After all scopes: merge permissions
       ↓
Does merged set contain required permission?
       ↓
  Yes → Allow
  No  → Deny (403)
```

Server-side enforcement. Never trust the client.

---

## 6. Key Design Decisions

### 6.1 Server-Rendered with Progressive Enhancement

The base application works without JavaScript. HTMX adds dynamic behavior (search results, form submissions, image previews) without shipping a full SPA framework. JavaScript is used only for features that genuinely require it (camera, QR scanning, file drag-and-drop, PWA).

### 6.2 Local Authentication with Optional 2FA

Authentication uses argon2 password hashing and HS256 JWT session cookies. No external auth service is required. TOTP two-factor authentication is optional per-user. Anti-bruteforce is enforced via per-account lockout in the database (shared across instances) and an in-process IP throttle.

### 6.3 No Local File Storage in Production

Uploaded images are processed in-memory and sent to S3-compatible object storage. The server never writes user uploads to the local filesystem permanently. This is essential for Vercel's serverless model.

### 6.4 Access Scopes over Direct Role Checks

Rather than checking `if user.role == "admin"` at every endpoint, the system evaluates Access Scopes. This provides fine-grained control and allows non-admin users to have scoped permissions.

### 6.5 Movement History as First-Class Entity

Item movements are recorded in a dedicated `item_movements` table. The current location is stored on the item for fast reads. The movement table provides the full audit trail.

### 6.6 Deterministic QR Codes

QR codes encode the stable item URL (`/item/<uuid>`). The UUID is immutable. QR images are generated on demand and cached. The QR content never changes even if the application's visual design changes.

---

## 7. Database Schema Summary

### Core Tables

| Table                | Purpose                              |
|----------------------|--------------------------------------|
| `users`              | Application users (local auth, email+password) |
| `items`              | Central inventory entity             |
| `categories`         | Hierarchical item categories         |
| `tags`               | Flat tag vocabulary                  |
| `item_tags`          | Many-to-many item ↔ tag             |
| `locations`          | Hierarchical physical locations      |
| `item_attributes`    | Key-value characteristics per item   |
| `item_relationships` | Connections between items            |
| `item_movements`     | Location change history              |
| `item_images`        | Image metadata (files in Supabase Storage) |
| `access_scopes`      | Named permission scopes              |
| `access_scope_rules` | Rules defining scope item coverage   |
| `access_scope_permissions` | Permissions granted within scope |
| `access_scope_users` | User assignments to scopes           |

### Indexes

- Full-text search index on `items` (name, description, SKU, serial number, manufacturer, model)
- Trigram indexes for fuzzy search
- B-tree indexes on foreign keys
- Composite indexes for common Access Scope evaluation queries

---

## 8. API Design

REST API at `/api/v1/`. Uses Pydantic schemas for request/response. Same authorization as HTML routes.

```
GET    /api/v1/items
POST   /api/v1/items
GET    /api/v1/items/{id}
PATCH  /api/v1/items/{id}
DELETE /api/v1/items/{id}
GET    /api/v1/search?q=...
GET    /api/v1/categories
GET    /api/v1/tags
GET    /api/v1/locations
GET    /api/v1/items/{id}/qr
GET    /api/v1/items/{id}/movements
```

---

## 9. Security Model

- Local authentication (email + password, argon2 hashing)
- Session-based authentication via signed JWT cookies (HS256, HttpOnly)
- Optional TOTP two-factor authentication per user
- Anti-bruteforce: per-account lockout after configurable failed attempts
- In-process IP throttle on login endpoint
- Authorization enforced server-side on every protected endpoint
- CSRF protection on state-changing HTML routes
- Content Security Policy headers
- No secrets exposed to client-side JavaScript
- Image upload validation (MIME, size, decompression bomb protection)

---

## 10. Deployment Architecture

```
Frontend (CDN / static)
    └── FastAPI application (serverless or container)
            ├── Database (PostgreSQL or SQLite)
            └── Object storage (S3-compatible)
```

Deployment is configuration-only: set `DATABASE_URL`, `SECRET_KEY`, `ADMIN_EMAIL`/`ADMIN_PASSWORD`, and `AWS_*`/`S3_BUCKET_NAME` variables and the same image/app runs anywhere — Vercel, DigitalOcean, AWS, bare metal.

No persistent local state. No background workers. No local file storage in production.

---

## 11. Development Workflow

1. Clone repository
2. Copy `.env.example` to `.env`, fill values (see README)
3. `uv sync` — install dependencies
4. `uv run uvicorn app.main:app --reload` — start dev server (SQLite by default, zero config)
5. Open `http://localhost:8000`

For PostgreSQL development, start a local database first:
`docker compose up -d db` and set `DATABASE_URL` in `.env`.

Migrations and admin bootstrap run automatically on startup.

### Code Quality

```bash
uv run ruff check app/ tests/        # Linting
uv run ruff format --check .         # Formatting
uv run mypy app/                     # Type checking
uv run pytest                        # Tests (SQLite-powered, fast)
```
