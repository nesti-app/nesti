# Nesti — Home Inventory Catalog

<p align="center">
  <img src="static/icons/nesti.png" alt="Nesti Logo" width="200">
</p>

A modern web application for managing a personal inventory of physical objects located in a house, garage, office, workshop and other locations.

## Features

- Item catalog with categories, tags, locations, and characteristics
- Hierarchical categories and locations
- QR code generation and scanning
- Thermal printer label generation (PNG)
- Image upload with automatic optimization and thumbnail generation
- Movement history tracking
- Item relationships (contains, part_of, accessory_of, etc.)
- Full-text search with filters
- Access Scope-based authorization
- Role-based access control (admin, editor, viewer)
- Complete data export/import (ZIP archive)
- Progressive Web App (PWA)
- Mobile-first responsive design
- Ukrainian primary UI, extensible to other languages
- Local authentication (email + password, argon2 hashing)
- Optional TOTP two-factor authentication (Google Authenticator / Authy)
- Anti-bruteforce protection (account lockout + IP throttle)

## Tech Stack

- **Backend:** Python 3.13+, FastAPI, SQLAlchemy 2.x (async), Alembic, PostgreSQL or SQLite
- **Frontend:** Jinja2, HTMX, Tailwind CSS, minimal vanilla JavaScript
- **Auth:** Local — email + password, argon2 hashing, HS256 JWT cookies (no external auth service)
- **Storage:** S3-compatible object storage (AWS, Supabase Storage, MinIO, rustfs, etc.)
- **Deployment:** Vercel (serverless), Docker, or bare metal

## Prerequisites

- [Git](https://git-scm.com/)
- [Python 3.13+](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Docker](https://docs.docker.com/get-docker/) or [Podman](https://podman.io/) (optional, for PostgreSQL)
- [Node.js](https://nodejs.org/) (only if building Tailwind CSS locally)
- [Vercel account](https://vercel.com/) (for production deployment)

## Quick Start (SQLite — zero setup)

```bash
git clone <repository-url>
cd nesti
uv sync

# Create .env with your settings
cp .env.example .env
# Edit .env: set SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
# DATABASE_URL defaults to sqlite+aiosqlite:///./data/nesti.db

# Start the server — migrations and admin bootstrap run automatically
uv run uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000). Log in with the admin credentials from your `.env`.

## Local Development (PostgreSQL)

### 1. Start PostgreSQL

```bash
docker compose up -d db
# or: podman compose up -d db
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
DATABASE_URL=postgresql+asyncpg://nesti:nesti@localhost:5432/nesti
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(64))">
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-secure-password
```

### 3. Start the server

```bash
uv run uvicorn app.main:app --reload
```

Migrations and admin bootstrap run automatically on first request.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_ENV` | No | `development` | `development` or `production` |
| `APP_URL` | No | `http://localhost:8000` | Application base URL |
| `SECRET_KEY` | **Yes** | — | Random secret for JWT session signing. Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./data/nesti.db` | Database URL. PostgreSQL: `postgresql+asyncpg://...`. SQLite: `sqlite+aiosqlite:///...` |
| `SETTINGS_FILE` | No | `.env` | Path to env-file for config. Real env vars always take precedence |
| `ADMIN_EMAIL` | No | — | Bootstrap admin email (created on startup if no user with this email exists) |
| `ADMIN_PASSWORD` | No | — | Bootstrap admin password (hashed with argon2) |
| `LOGIN_MAX_ATTEMPTS` | No | `5` | Failed login attempts before account lockout |
| `LOGIN_LOCKOUT_SECONDS` | No | `900` | Lockout duration in seconds (15 min) |
| `IP_THROTTLE_PER_MINUTE` | No | `20` | Max login attempts per IP per minute (per-process; see note below) |

### S3-Compatible Storage

Storage is enabled when `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set.

| Variable | Required | Default | Description |
|---|---|---|---|
| `AWS_ACCESS_KEY_ID` | **Yes** (for storage) | — | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | **Yes** (for storage) | — | S3 secret key |
| `AWS_DEFAULT_REGION` | No | `us-east-1` | S3 region |
| `AWS_ENDPOINT_URL` | No | — | S3 endpoint. Set for Supabase Storage, MinIO, rustfs. Empty = classic AWS |
| `S3_BUCKET_NAME` | No | `inventory-images` | Bucket name |
| `S3_FORCE_PATH_STYLE` | No | `true` | Use path-style addressing (required for MinIO, rustfs) |

### Image Processing

| Variable | Default | Description |
|---|---|---|
| `MAX_UPLOAD_SIZE` | `10485760` (10 MB) | Max upload size in bytes |
| `IMAGE_MAX_DIMENSION` | `2400` | Max dimension for optimized images |
| `THUMBNAIL_MAX_DIMENSION` | `256` | Max dimension for thumbnails |
| `LABEL_DPI` | `203` | DPI for label generation |

> **IP throttle note:** the sliding-window IP throttle is in-memory per process.
> Sufficient for a single container; for multiple replicas or Kubernetes, consider
> a shared rate limiter (Redis) or rely on the per-account lockout in the database.

## Authentication

### How It Works

- **Password hashing:** argon2 (via `pwdlib`)
- **Session:** HS256 JWT stored in an `HttpOnly` cookie (`nesti_session`), signed with `SECRET_KEY`, expires after 7 days
- **Two-factor (TOTP):** optional per-user; when enabled, login requires a second step with a 6-digit code from an authenticator app
- **Anti-bruteforce:** 5 failed attempts → account locked for 15 minutes. IP-level throttle as additional layer

### Admin Bootstrap

Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in your environment. On startup, if no user with that email exists, one is created with the `admin` role. If the user already exists but has no password, the password is set.

### Two-Factor Authentication

1. Go to **Profile → Two-Factor Authentication**
2. Click **Enable** — scan the QR code with your authenticator app
3. Enter the current 6-digit code to confirm
4. Next login will require the code after entering your password

Admins can disable 2FA for any user from the user detail page.

## Production Deployment

### 1. Push to GitHub

```bash
git init && git add . && git commit -m "Initial commit"
git remote add origin <repository-url>
git push -u origin main
```

### 2. Connect to Vercel

1. Go to [vercel.com](https://vercel.com/)
2. Click **Add New Project** → Import the GitHub repository
3. Vercel will detect the Python project automatically

### 3. Configure Vercel

Create `vercel.json` in the project root (if not already present):

```json
{
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

### 4. Set Environment Variables

In the Vercel dashboard → **Settings → Environment Variables**, add:

| Variable | Example |
|---|---|
| `SECRET_KEY` | `<random 64-byte token>` |
| `DATABASE_URL` | `postgresql+asyncpg://postgres.<ref>:<password>@aws-1-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require` |
| `APP_ENV` | `production` |
| `ADMIN_EMAIL` | `admin@yourdomain.com` |
| `ADMIN_PASSWORD` | `<secure password>` |
| `AWS_ACCESS_KEY_ID` | `<your S3 key>` |
| `AWS_SECRET_ACCESS_KEY` | `<your S3 secret>` |
| `AWS_ENDPOINT_URL` | *(empty for classic AWS, or set for Supabase/MinIO)* |
| `S3_BUCKET_NAME` | `inventory-images` |

**Important for Supabase PostgreSQL:** use the **Session pooler** (port 5432), not the direct host. Add `?sslmode=require` to the connection string.

**Never** commit actual secrets to the repository.

### 5. Database Migrations

**Migrations run automatically** on application startup. No manual step needed.

To run manually:

```bash
DATABASE_URL="<production-url>" uv run alembic upgrade head
```

### 6. Verify Deployment

1. Open `https://your-project.vercel.app/health` — should return OK
2. Log in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`
3. Test item CRUD and image upload
4. Verify HTTPS and PWA

## Testing

```bash
uv run pytest                          # All tests
uv run pytest --cov=app --cov-report=term-missing  # With coverage
uv run ruff check app/ tests/          # Linting
uv run ruff format --check .           # Formatting check
uv run mypy app/                       # Type checking
```

## Project Documentation

- [SPECIFICATION.md](SPECIFICATION.md) — Full technical specification
- [ARCHITECTURE.md](ARCHITECTURE.md) — Architecture, permission matrix, design decisions

## License

MIT
