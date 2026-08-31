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

## Tech Stack

- **Backend:** Python 3.13+, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL
- **Frontend:** Jinja2, HTMX, Tailwind CSS, minimal vanilla JavaScript
- **Auth:** Supabase Auth
- **Storage:** Supabase Storage (images), optionally via its S3-compatible API (fully async)
- **Deployment:** Vercel (serverless)

## Prerequisites

- [Git](https://git-scm.com/)
- [Python 3.13+](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Docker](https://docs.docker.com/get-docker/) or [Podman](https://podman.io/) (optional, for local PostgreSQL)
- [Node.js](https://nodejs.org/) (only if building Tailwind CSS locally)
- [Supabase account](https://supabase.com/)
- [Vercel account](https://vercel.com/)

## Supabase Setup

### 1. Create Project

1. Go to [supabase.com](https://supabase.com/) and sign in
2. Click "New Project"
3. Choose organization, set project name and database password
4. Select a region close to your users
5. Wait for the project to be provisioned

### 2. Database

The PostgreSQL database is created automatically with the Supabase project.

Note the connection string from **Settings → Database → Connection string → URI**. Use the "Transaction" mode URI for the application.

### 3. Auth Configuration

1. Go to **Authentication → Providers**
2. Enable the desired providers (email, OAuth, etc.)
3. Go to **Authentication → URL Configuration**
4. Add your production URL to **Redirect URLs**: `https://your-domain.vercel.app/auth/callback`
5. Add your local URL for development: `http://localhost:8000/auth/callback`

### 4. Storage Bucket

1. Go to **Storage**
2. Create a new bucket named `inventory-images`
3. Set the bucket to **private** (not public)
4. Add the following bucket policy:

```sql
-- Allow authenticated users to read images
CREATE POLICY "Authenticated read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'inventory-images' AND auth.role() = 'authenticated');

-- Allow authenticated users to upload images
CREATE POLICY "Authenticated upload access"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'inventory-images' AND auth.role() = 'authenticated');

-- Allow authenticated users to delete their own uploads
CREATE POLICY "Authenticated delete access"
ON storage.objects FOR DELETE
USING (bucket_id = 'inventory-images' AND auth.role() = 'authenticated');
```

### 5. Obtain Keys

Go to **Settings → API Keys** and note:

- **Project URL** (e.g., `https://xyzcompany.supabase.co`)
- **Publishable key** (`sb_publishable_...`) — used for public/auth calls
- **Secret key** (`sb_secret_...`) — server-side only, never expose to client
- Legacy **anon** / **service_role** keys are also supported as fallbacks but
  the modern publishable/secret keys are preferred.

## Local Setup

### 1. Clone and Install

```bash
git clone <repository-url>
cd nesti
uv sync
```

### 2. Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in all values:

| Variable                   | Description                                           |
|----------------------------|-------------------------------------------------------|
| `APP_ENV`                  | `development` or `production`                         |
| `APP_URL`                  | Application base URL (e.g., `http://localhost:8000`)  |
| `SECRET_KEY`               | Random secret for session signing (generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`) |
| `DATABASE_URL`             | PostgreSQL connection string (asyncpg / pooler)       |
| `SUPABASE_URL`             | Supabase project URL                                  |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (`sb_publishable_...`)       |
| `SUPABASE_SECRET_KEY`      | Supabase secret key (`sb_secret_...`) — server-side only |
| `SUPABASE_STORAGE_BUCKET`  | Storage bucket name (default: `inventory-images`)     |
| `S3_ENDPOINT_URL`          | S3-compatible endpoint (e.g. `https://<ref>.supabase.co/storage/v1/s3`). Set to enable S3 backend |
| `S3_ACCESS_KEY_ID`         | S3 access key ID (Supabase → Storage → Settings → S3 API Access) |
| `S3_SECRET_ACCESS_KEY`     | S3 secret access key (same location)                  |
| `S3_BUCKET_NAME`           | Bucket used via S3 API (defaults to `SUPABASE_STORAGE_BUCKET`) |
| `S3_REGION`                | S3 region (default: `us-east-1`)                      |
| `MAX_UPLOAD_SIZE`          | Max upload size in bytes (default: `10485760` = 10MB) |
| `IMAGE_MAX_DIMENSION`      | Max dimension for optimized images (default: `2400`)  |
| `THUMBNAIL_MAX_DIMENSION`  | Max dimension for thumbnails (default: `256`)         |
| `LABEL_DPI`                | DPI for label generation (default: `203`)             |

> **Key migration:** the modern `SUPABASE_PUBLISHABLE_KEY` /
> `SUPABASE_SECRET_KEY` are preferred. The legacy `SUPABASE_ANON_KEY` and
> `SUPABASE_SERVICE_ROLE_KEY` are still supported as fallbacks for backward
> compatibility; the app uses whichever is set, preferring the modern keys.

### 3. Local PostgreSQL (Optional)

If you prefer a local database for development:

```bash
docker compose up -d
```

or with Podman:

```bash
podman compose up -d
```

This starts a PostgreSQL instance on port 5432. Update `DATABASE_URL` in `.env` accordingly:

```
DATABASE_URL=postgresql+asyncpg://nesti:nesti@localhost:5432/nesti
```

### 4. Database Migrations

```bash
uv run alembic upgrade head
```

### 5. Development Server

```bash
uv run uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

## Testing

### Unit and Integration Tests

```bash
uv run pytest
```

### With Coverage

```bash
uv run pytest --cov=app --cov-report=term-missing
```

### Linting

```bash
uv run ruff check .
```

### Formatting Check

```bash
uv run ruff format --check .
```

### Format Code

```bash
uv run ruff format .
```

### Type Checking

```bash
uv run mypy .
```

### E2E Tests (Playwright)

```bash
uv run playwright install
uv run pytest tests/e2e/
```

## Production Deployment

### 1. Create GitHub Repository

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <repository-url>
git push -u origin main
```

### 2. Connect to Vercel

1. Go to [vercel.com](https://vercel.com/)
2. Click "Add New Project"
3. Import the GitHub repository
4. Vercel will detect the Python project

### 3. Configure Vercel

Create `vercel.json` in the project root:

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

### 4. Environment Variables

In the Vercel dashboard, go to **Settings → Environment Variables** and add all variables from `.env.example` with production values.

**Important:** the `DATABASE_URL` must use the **asyncpg** driver prefix —
`postgresql+asyncpg://...`. The connection string shown in the Supabase
dashboard is usually plain `postgresql://...`, which SQLAlchemy maps to the
`psycopg2` driver (not installed) and breaks every database query with a 500.
The app automatically normalizes plain `postgres://` / `postgresql://` URLs
to `postgresql+asyncpg://` and adds `ssl=require` for Supabase Cloud hosts,
but using the correct prefix avoids any confusion.
**Use the Supabase pooler (session pooler, port 5432), not the direct host.**
The direct host (`db.<ref>.supabase.co:5432`) is often unreachable from
serverless environments (Vercel) and causes a 500 on every page. The
correct working form looks like:
```
postgresql://postgres.<project-ref>:<DB_PASSWORD>@aws-1-eu-west-1.pooler.supabase.com:5432/postgres
```
Copy the exact **Session pooler** connection string from
Supabase → **Connect** (take care to use the **5432** port). Prefer the
session pooler (5432) over the transaction pooler (6543) unless you need
pgbouncer-mode semantics.

**Never** commit actual secrets to the repository.

### 5. Database Migrations

**Migrations run automatically** on application startup — you don't need to run
them manually. On the first deploy (and every subsequent one), the app applies
any pending Alembic migrations against the `DATABASE_URL` before serving
requests.

If you ever need to run them manually against the production database:

```bash
DATABASE_URL="<production-database-url>" uv run alembic upgrade head
```

### 6. First User Becomes Admin

The very first user who successfully signs in to a fresh deployment (an empty
`users` table) is automatically created in the database with the **`admin`**
role. This means you don't need to provision an admin manually — just sign up
or log in through Supabase Auth and that account becomes the administrator.
Afterwards you can manage other users (viewer/editor/admin) from
**Admin → Users**.

Subsequent users who are auto-created on login default to the `viewer` role.

### 7. Verify Deployment

1. Open `https://your-project.vercel.app/health` — should return OK
2. Test authentication flow
3. Test image upload
4. Test QR code generation and scanning
5. Verify HTTPS is enabled
6. Verify PWA installation works

## Project Documentation

- [SPECIFICATION.md](SPECIFICATION.md) — Full technical specification
- [ARCHITECTURE.md](ARCHITECTURE.md) — Architecture, permission matrix, design decisions

## License

MIT
