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
- **Storage:** Supabase Storage (images)
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

Go to **Settings → API** and note:

- **Project URL** (e.g., `https://xyzcompany.supabase.co`)
- **anon public key** (starts with `eyJ...`)
- **service_role key** (starts with `eyJ...` — keep this secret, never expose to client)

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
| `DATABASE_URL`             | PostgreSQL connection string (transaction mode)        |
| `SUPABASE_URL`             | Supabase project URL                                  |
| `SUPABASE_ANON_KEY`        | Supabase anon/public key                              |
| `SUPABASE_SERVICE_ROLE_KEY`| Supabase service-role key (server-side only)          |
| `SUPABASE_STORAGE_BUCKET`  | Storage bucket name (default: `inventory-images`)     |
| `MAX_UPLOAD_SIZE`          | Max upload size in bytes (default: `10485760` = 10MB)|
| `IMAGE_MAX_DIMENSION`      | Max dimension for optimized images (default: `2400`)  |
| `THUMBNAIL_MAX_DIMENSION`  | Max dimension for thumbnails (default: `256`)         |
| `LABEL_DPI`                | DPI for label generation (default: `203`)             |

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

**Never** commit actual secrets to the repository.

### 5. Run Migrations

After the first deploy, run migrations against the production database:

```bash
DATABASE_URL="<production-database-url>" uv run alembic upgrade head
```

Or connect to the Supabase database directly and run migrations.

### 6. Verify Deployment

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
