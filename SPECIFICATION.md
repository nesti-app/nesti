# Home Inventory Catalog — Technical Specification

## 1. Project Overview

Build a modern web application for managing a personal inventory of physical objects located in a house, garage, office, workshop and other locations.

The application is a **home inventory management system**, not an e-commerce application.

Each physical object is represented by an `Item` and has:

- unique permanent UUID;
- name;
- description;
- category;
- tags;
- physical location;
- optional parent item;
- related items;
- photographs;
- technical characteristics;
- QR code;
- purchase information;
- notes;
- movement history;
- creation/update metadata.

The application must support:

- authentication;
- multiple users;
- administrator-managed users;
- granular access control;
- CRUD operations;
- fast search;
- QR-code scanning;
- QR-code generation;
- item movement history;
- image optimization;
- printable labels;
- PWA installation;
- complete data export;
- complete data import;
- backup/restore.

The primary language of the UI is Ukrainian.

The architecture must allow adding English and other languages later.

---

# 2. Primary Goals

The application must be:

- simple to use;
- fast;
- mobile-first;
- desktop-friendly;
- secure;
- portable;
- inexpensive to host;
- easy to maintain;
- easy to back up;
- independent from a particular hosting provider;
- suitable for several thousand inventory items.

The application must work well when used directly next to physical objects.

Typical workflow:

```text
Find physical object
        ↓
Open application
        ↓
Scan QR code
        ↓
Open item
        ↓
View information
        ↓
Move/edit/add photo/etc.
```

Another workflow:

```text
Find physical object
        ↓
Open application
        ↓
Search by name
        ↓
Open item
        ↓
View location / QR / history
```

---

# 3. Technology Stack

## Backend

Use:

- Python 3.13+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Jinja2

Use type hints throughout the project.

Use async database access where appropriate.

Keep business logic outside HTTP route handlers.

---

# 4. Frontend

Use server-rendered HTML with progressive enhancement.

Preferred stack:

- Jinja2
- HTMX
- Tailwind CSS
- minimal vanilla JavaScript

Do NOT use React, Vue, Angular or another SPA framework for the initial implementation.

The application should remain primarily Python-based.

JavaScript should be used where browser functionality requires it, such as:

- camera access;
- QR scanning;
- image previews;
- drag & drop;
- interactive forms;
- PWA functionality.

The application should remain usable without JavaScript for basic navigation and CRUD wherever practical.

---

# 5. Database

Use PostgreSQL.

Primary hosted option:

- Supabase PostgreSQL.

The application must not depend on Supabase-specific database functionality unless there is a strong reason.

Use:

- SQLAlchemy models;
- Alembic migrations;
- PostgreSQL indexes;
- PostgreSQL constraints.

Every database schema change must be represented by an Alembic migration.

Do not use SQLite in production.

SQLite may optionally be used for very lightweight local development only if it does not complicate the architecture.

Prefer PostgreSQL locally to keep development and production environments consistent.

---

# 6. Authentication

Use Supabase Auth initially.

Authentication must be abstracted behind an application authentication service.

Do not spread Supabase-specific authentication code throughout the application.

The application must support:

- login;
- logout;
- session handling;
- authenticated routes;
- user identification;
- administrator identification.

Do not implement password storage in the application database.

Do not expose the Supabase service-role key to the browser.

---

# 7. Users

Administrators must be able to manage application users.

The administrator UI must provide:

- list users;
- add/invite user;
- deactivate user;
- reactivate user;
- change user role;
- view user's access scopes.

Initial roles:

```text
admin
editor
viewer
```

### Admin

Can:

- manage users;
- manage access;
- create/edit/delete items;
- manage categories;
- manage tags;
- manage locations;
- manage relationships;
- view movement history;
- perform import/export;
- manage application settings.

### Editor

Can:

- view permitted items;
- create items;
- edit permitted items;
- upload images;
- move permitted items;
- manage relationships where permitted.

Cannot:

- manage users;
- manage global access policies;
- perform destructive administrative operations outside permitted scopes.

### Viewer

Can:

- view permitted items;
- search permitted items;
- scan QR codes;
- view item history if granted.

Cannot modify inventory.

The exact permission matrix should be documented in `ARCHITECTURE.md`.

---

# 8. Access Scope

## 8.1 General Concept

Do NOT give users access directly based only on category or location.

Instead implement a first-class concept called:

**Access Scope**

An Access Scope represents a logical group of inventory objects to which a user or group of users can receive permissions.

This provides flexibility without coupling authorization directly to the physical organization of inventory.

---

# 8.2 Access Scope Examples

Example:

```text
Garage Tools
    Location = Garage
    Category = Tools
```

Another:

```text
Server Equipment
    Location = Server Room
```

Another:

```text
Photography
    Category = Photography
    Tags = camera, lens
```

Another:

```text
Specific Items
    Item A
    Item B
    Item C
```

Access scopes should support multiple conditions.

---

# 8.3 Access Scope Rules

An Access Scope may contain one or more rules.

Possible rule types:

```text
location
category
tag
specific_item
```

A future implementation may support additional rule types.

Example:

```text
Scope: Garage Tools

Rules:
    location = Garage
    category = Tools
```

The system must clearly define whether multiple rules are:

- AND conditions;
- OR conditions.

For the initial implementation:

**Rules inside one Access Scope should be combined using AND semantics unless explicitly marked otherwise.**

This prevents accidentally exposing too many items.

Example:

```text
location = Garage
AND
category = Tools
```

means:

> Tools located in Garage.

---

# 8.4 Access Scope Permissions

An Access Scope should grant one or more permissions:

```text
view
create
edit
move
delete
manage_images
```

Do not automatically grant all permissions.

Example:

```text
Scope: Garage Tools

Igor:
    view
    edit
    move

Anna:
    view
```

---

# 8.5 Access Scope UI/UX

The Access Scope interface is a critical part of the application.

Do NOT expose raw database IDs or technical permission structures to the user.

The UI must be visual and understandable.

Recommended interface:

```text
Access Scopes

┌─────────────────────────────────────────────┐
│ Garage Tools                                │
│                                             │
│ 📍 Garage                                   │
│ 🏷 Tools                                    │
│                                             │
│ 3 users                                      │
│                                             │
│ [Manage]                                    │
└─────────────────────────────────────────────┘
```

When creating a scope:

```text
Create Access Scope

Name:
[ Garage Tools                         ]

Description:
[ Tools stored in the garage            ]

Include items where:

Location
[ Garage ▼ ]

Category
[ Tools ▼ ]

Tags
[ + Add tag ]

Specific items
[ + Add items ]

Permissions:

☑ View
☑ Edit
☑ Move
☐ Delete
☑ Manage images

Users:

[ + Add users ]

             [Cancel] [Create]
```

The UI should show a live summary:

```text
This scope currently matches 47 items.

Users with access:
    Igor
    Anna
```

Before saving changes, display the estimated impact:

```text
Changing this scope will affect:

47 items
2 users
```

This is important to prevent accidental data exposure.

---

# 8.6 Access Scope Evaluation

Authorization must be enforced server-side.

Never rely on UI visibility.

For every item request, the backend must verify:

```text
User
 ↓
Permissions
 ↓
Access Scopes
 ↓
Does this item match?
 ↓
Allow / Deny
```

A user must never be able to access an unauthorized item simply by manually changing its UUID in the URL.

The same authorization rules must apply to:

- HTML routes;
- API;
- image access;
- downloads;
- QR endpoints;
- movement history;
- exports.

---

# 9. Item Model

The central entity is `Item`.

Suggested fields:

```text
id                  UUID PRIMARY KEY
name                TEXT NOT NULL
description         TEXT

category_id         UUID NULL
location_id         UUID NULL
parent_item_id      UUID NULL

manufacturer        TEXT NULL
model               TEXT NULL
serial_number       TEXT NULL
sku                 TEXT NULL

purchase_date       DATE NULL
purchase_price      NUMERIC NULL
currency            TEXT NULL

notes               TEXT NULL

created_at          TIMESTAMP NOT NULL
updated_at          TIMESTAMP NOT NULL
created_by          UUID NULL
updated_by          UUID NULL
```

The UUID is immutable.

Users must never manually change the UUID.

---

# 10. QR Code

QR code is the only supported machine-readable identifier.

Do NOT implement barcode functionality.

Do NOT add barcode fields.

Do NOT add barcode scanning.

Do NOT add barcode generation.

---

# 11. QR Code Architecture

The QR code must contain a stable application URL.

Example:

```text
https://inventory.example.com/item/<uuid>
```

The exact domain must come from configuration.

Never hard-code the production domain.

The QR code must remain valid if the visual design of the application changes.

The UUID must remain immutable.

The QR image itself is a derived asset.

The UUID is the source of truth.

---

# 12. QR Code Features

The item page must provide:

- display QR;
- download QR;
- generate printable label;
- share QR image;
- print label.

QR generation must be deterministic.

The generated QR must have sufficient error correction for physical labels.

---

# 13. Thermal Printer Label

The application must support generating a printable label image rather than implementing a printer-specific backend.

When the user clicks:

```text
Print label
```

show a label configuration dialog.

Example:

```text
Print label

Select label size:

○ 12 × 30 mm
○ 15 × 30 mm
○ 15 × 40 mm
○ 20 × 30 mm
○ 20 × 50 mm
○ Custom

[Cancel] [Generate label]
```

The application must support predefined sizes and allow a custom size if practical.

The generated label should contain at minimum:

- QR code;
- item name;
- optionally short ID.

Example:

```text
┌─────────────────────────┐
│                         │
│       █████████         │
│       █ QR  ███         │
│       █████████         │
│                         │
│ Network Switch          │
│ A7F3-21                  │
└─────────────────────────┘
```

The exact layout should adapt to label dimensions.

---

# 14. Label Image Generation

The server or browser may generate a PNG depending on the implementation.

The result must be a high-resolution PNG suitable for thermal printing.

The generated image must respect the requested physical dimensions.

Calculate pixel dimensions from:

```text
pixels = millimeters / 25.4 * DPI
```

Use an appropriate DPI, for example 203 DPI, unless another printer-compatible DPI is configured.

Do not assume all thermal printers use the same DPI.

The label generator must be isolated as a reusable service.

---

# 15. Mobile Label Workflow

On mobile devices:

```text
Item
 ↓
Print label
 ↓
Select label size
 ↓
Generate PNG
 ↓
Share
```

The application should use the browser's Web Share API where available.

The generated PNG should be offered to the native share sheet.

The user can then select:

- printer application;
- NIIMBOT application;
- Meow Machine application;
- file sharing;
- messaging;
- cloud storage;
- other compatible application.

Do not hard-code a dependency on NIIMBOT.

Do not require a direct Bluetooth connection from the web application.

The web application should produce a portable image that can be shared to the appropriate printer application.

---

# 16. Desktop Label Workflow

On desktop:

```text
Item
 ↓
Print label
 ↓
Select label size
 ↓
Generate PNG
 ↓
Download PNG
```

The UI should offer:

```text
Download PNG
```

and optionally:

```text
Print
```

if the browser supports direct printing.

The downloaded image must be suitable for further use with desktop printer software.

---

# 17. Image Management

Each item can have multiple photographs.

Original uploaded images must NOT be permanently stored.

The application must process uploaded images.

For every uploaded image generate:

1. thumbnail/icon;
2. optimized high-quality image.

Store only processed versions.

Do not retain the original multi-megabyte upload.

---

# 18. Image Processing

Recommended outputs:

```text
thumbnail
optimized
```

Example:

```text
thumbnail:
    ~256px maximum dimension

optimized:
    ~1600–2400px maximum dimension
```

Exact dimensions should be configurable.

The optimized image should be compressed appropriately.

Preferred formats:

```text
WebP
```

JPEG may be used where compatibility requires it.

PNG should be preserved for images where lossless output is useful.

Do not blindly convert every image to JPEG.

---

# 19. Image Upload Security

Uploaded files are untrusted.

Requirements:

- maximum upload size;
- MIME validation;
- actual image decoding;
- extension validation;
- filename sanitization;
- generated storage filenames;
- image decompression bomb protection where practical;
- reject executable files;
- strip unnecessary metadata where appropriate.

Do not expose original filenames as storage identifiers.

---

# 20. Image Storage

Use Supabase Storage.

Example:

```text
inventory-images/
    <item-uuid>/
        thumbnail.webp
        optimized.webp
        second-thumbnail.webp
        second-optimized.webp
```

The database should contain metadata such as:

```text
id
item_id
storage_path
mime_type
width
height
size_bytes
sort_order
is_primary
created_at
created_by
```

Do not store binary image content in PostgreSQL.

---

# 21. Item Characteristics

Different item categories have different properties.

Do not create hundreds of nullable columns in `items`.

Use a separate characteristics table:

```text
item_attributes

id
item_id
name
value
unit
sort_order
```

Example:

```text
Power     | 850  | W
Voltage   | 230  | V
Capacity  | 2    | TB
RAM       | 32   | GB
Color     | Black |
```

This must be designed so category-specific structured attributes can be added later.

---

# 22. Categories

Categories support hierarchy.

Example:

```text
Electronics
├── Computers
│   ├── Laptops
│   └── Accessories
├── Networking
└── Audio

Tools
├── Power Tools
└── Hand Tools
```

Fields:

```text
id
name
slug
description
parent_category_id
created_at
updated_at
```

---

# 23. Tags

Implement many-to-many tags.

Tables:

```text
tags
item_tags
```

Examples:

```text
important
warranty
expensive
spare
broken
to-sell
```

Tags may also be used as Access Scope filters.

---

# 24. Locations

Locations must support hierarchy.

Example:

```text
House
├── Basement
│   ├── Storage Room
│   └── Server Room
├── Garage
├── Ground Floor
│   ├── Kitchen
│   └── Living Room
└── First Floor
    ├── Bedroom
    └── Office
```

Fields:

```text
id
name
description
parent_location_id
created_at
updated_at
```

---

# 25. Item Relationships

Items may be related.

Support:

```text
contains
part_of
accessory_of
connected_to
used_with
replacement_for
related_to
```

Create:

```text
item_relationships

id
source_item_id
target_item_id
relationship_type
created_at
created_by
```

Prevent invalid relationships such as an item relating to itself.

---

# 26. Parent Item

Items may have a parent item.

Example:

```text
Computer
├── SSD
├── RAM
└── Power Adapter
```

Use:

```text
parent_item_id
```

for hierarchical ownership/containment.

Do not use parent-child hierarchy as a replacement for generic item relationships.

---

# 27. Movement History

Movement history is a first-class feature.

Do NOT implement movement history by simply overwriting `location_id`.

The current location remains on the item:

```text
items.location_id
```

Additionally maintain:

```text
item_movements
```

Suggested fields:

```text
id
item_id

from_location_id
to_location_id

moved_at
moved_by

reason
notes
```

---

# 28. Movement Workflow

When an item's location changes:

```text
Current location:
Garage

New location:
Basement / Storage Room

Reason:
Moved for renovation

[Cancel] [Move item]
```

On confirmation:

1. create movement history record;
2. update `items.location_id`;
3. update `updated_at`;
4. record the user.

These operations must occur in one database transaction.

---

# 29. Movement History UI

The item page should display a timeline.

Example:

```text
Movement history

25 Aug 2026
📍 Garage → Basement / Storage Room
Moved by Igor
Reason: Renovation

12 Aug 2026
📍 Office → Garage
Moved by Igor
Reason: Storage
```

The timeline should be easy to understand on mobile.

The full history must be accessible.

---

# 30. Search

Search is a core feature.

Search must support:

- name;
- UUID;
- description;
- SKU;
- serial number;
- manufacturer;
- model;
- tags.

Search should be fast.

Do not retrieve all items into Python and filter there.

Use PostgreSQL indexes and appropriate full-text/trigram search.

---

# 31. Global Search UX

The application should have a persistent search field.

Example:

```text
🔍 Search inventory...
```

Search results should appear quickly.

Support:

- keyboard navigation on desktop;
- touch-friendly results on mobile;
- category filter;
- location filter;
- tag filter;
- sorting;
- pagination.

Search result example:

```text
┌──────────────────────────────────┐
│ 📷 Network Switch                │
│ Electronics / Networking        │
│ 📍 Garage                        │
│ ID: A7F3-21                      │
└──────────────────────────────────┘
```

---

# 32. QR Scanner

Provide a dedicated QR scanner page.

Workflow:

```text
Scan QR
    ↓
Camera permission
    ↓
Detect QR
    ↓
Validate payload
    ↓
Open item
```

Only accept:

- application-domain item URLs;
- recognized UUID values.

Do not automatically navigate to arbitrary external URLs encoded in QR codes.

Provide manual input fallback.

---

# 33. Item Page

The item page should contain:

```text
Item name
Category
Location
Primary image
Gallery
Description
Characteristics
Tags
Related items
Parent item
QR code
Movement history
Metadata
```

Actions:

```text
Edit
Move
Add photo
Print label
Download QR
Share
Delete
```

Actions must depend on permissions.

---

# 34. Item Sharing

The application should support sharing an item URL.

The item URL must be stable:

```text
/item/<uuid>
```

On mobile use Web Share API when available.

Otherwise copy URL to clipboard.

Access control still applies.

A shared URL must not bypass authentication or Access Scope restrictions.

---

# 35. Dashboard

Dashboard should display:

- total items;
- categories;
- locations;
- recent items;
- recently updated items;
- recently moved items;
- items without images;
- items without category;
- items without location;
- quick search;
- scan QR;
- add item.

Statistics must be calculated using SQL aggregation.

Do not load the entire inventory just to calculate counts.

---

# 36. PWA

The application must be installable as a Progressive Web App.

Requirements:

- Web App Manifest;
- application icon;
- favicon;
- appropriate theme colors;
- service worker;
- HTTPS;
- responsive layout;
- standalone display mode.

When installed on a phone or desktop:

```text
User clicks application icon
        ↓
Browser opens
        ↓
Application uses standalone mode
        ↓
UI looks and behaves like a native application
```

The application should hide unnecessary browser-like navigation UI where the browser supports standalone PWA mode.

---

# 37. PWA Installation

The UI should provide an unobtrusive:

```text
Install application
```

option when installation is available.

Do not display an installation prompt when the browser does not support it.

The PWA must have proper icons.

Provide at least:

```text
192x192
512x512
```

icons.

The application should support desktop PWA installation where supported.

---

# 38. Offline Support

Full offline inventory editing is NOT required for MVP.

However, PWA architecture should allow future offline support.

At minimum cache:

- application shell;
- static assets;
- icons.

Do not cache sensitive inventory data indiscriminately.

---

# 39. API

Expose a clean REST API.

Prefix:

```text
/api/v1
```

Examples:

```text
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

The API must use the same authorization system as the HTML interface.

Do not expose SQLAlchemy models directly.

Use Pydantic request/response schemas.

---

# 40. Import / Export

The application must support complete inventory export.

The export must be a single archive:

```text
inventory-YYYY-MM-DD.zip
```

The archive is intended for:

- backup;
- migration;
- disaster recovery;
- moving to another hosting provider;
- development/testing.

---

# 41. Archive Structure

Recommended structure:

```text
inventory-2026-08-25.zip

├── manifest.json
├── items.json
├── categories.json
├── tags.json
├── locations.json
├── item_attributes.json
├── item_relationships.json
├── item_movements.json
├── users.json
│
└── images/
    ├── <item-uuid>/
    │   ├── 001.webp
    │   ├── 002.webp
    │   └── ...
    │
    └── <another-item-uuid>/
        └── 001.webp
```

Do not include:

- passwords;
- authentication secrets;
- session tokens;
- Supabase credentials;
- service-role keys.

---

# 42. Manifest

The archive must contain:

```json
{
  "format": "home-inventory",
  "schema_version": 1,
  "created_at": "...",
  "application_version": "...",
  "image_format": "webp"
}
```

The `schema_version` is mandatory.

Future versions must provide migration logic for older archive formats where practical.

---

# 43. JSON Data

Use JSON for structured inventory data.

Objects must preserve UUID relationships.

Example:

```json
{
  "id": "uuid",
  "name": "Network Switch",
  "category_id": "uuid",
  "location_id": "uuid",
  "parent_item_id": null
}
```

Never export relationships only by array position.

Always use stable IDs.

---

# 44. Image Export

Export processed images, not original uploads.

The archive should contain the optimized application images.

The export must preserve:

- item relationship;
- filename;
- image order;
- primary image state;
- image metadata.

---

# 45. Import

Import must support:

```text
Upload ZIP
    ↓
Validate archive
    ↓
Validate manifest
    ↓
Validate schema version
    ↓
Validate JSON
    ↓
Validate references
    ↓
Validate images
    ↓
Show import preview
    ↓
Confirm
    ↓
Import
```

Never immediately modify the database after upload.

First validate the entire archive.

The UI must show a summary before import.

Example:

```text
Import preview

Items:              1,248
Categories:            32
Locations:             18
Tags:                  47
Images:             2,734
Movements:          1,109

Warnings:               3
Errors:                 0

[Cancel] [Import]
```

If validation fails, do not partially import data.

Use a transaction or staged import strategy.

---

# 46. Export Authorization

Full export must be available only to administrators initially.

The exported archive may contain sensitive information about the contents of the home.

Never expose the export endpoint to unauthorized users.

---

# 47. Deployment

Primary hosting target:

**Vercel**

The application must remain portable.

Possible alternative deployment platforms:

- Render;
- Railway;
- Fly.io;
- self-hosted Docker;
- other Python-compatible hosting.

Do not make business logic dependent on Vercel.

---

# 48. Vercel Architecture

Use Vercel's Python runtime for FastAPI.

The application must not require:

- persistent local filesystem;
- persistent background workers;
- long-running local processes;
- local image storage;
- local SQLite production database.

Uploaded images must be stored in Supabase Storage.

Database must be external PostgreSQL.

---

# 49. Hosting Documentation

`README.md` MUST contain a complete deployment guide.

A new developer must be able to deploy the application by following the README without guessing missing steps.

The README must document:

## Prerequisites

- Git;
- Python;
- uv;
- Node.js if required for frontend build;
- Docker/Podman optional;
- Supabase account;
- Vercel account.

## Supabase setup

Document:

1. create project;
2. create PostgreSQL database;
3. configure Auth;
4. configure storage bucket;
5. obtain required keys;
6. configure redirect URLs;
7. configure security policies where required.

## Local setup

Document:

```bash
git clone ...
cd ...
uv sync
cp .env.example .env
```

Then explain every environment variable.

## Database setup

Document:

```bash
uv run alembic upgrade head
```

## Development server

Document:

```bash
uv run uvicorn app.main:app --reload
```

## Testing

Document:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Production deployment

Document:

1. create GitHub repository;
2. connect repository to Vercel;
3. configure build/runtime settings;
4. configure environment variables;
5. configure Supabase;
6. run migrations;
7. deploy;
8. verify `/health`;
9. verify authentication;
10. verify image upload;
11. verify QR URLs.

---

# 50. Local Development with Containers

Provide Docker support.

Preferred:

```text
Dockerfile
docker-compose.yml
```

or:

```text
compose.yaml
```

The local environment should provide at least:

```text
Application
PostgreSQL
```

Supabase can remain an external dependency for Auth and Storage during local development if implementing a complete local Supabase stack would add unnecessary complexity.

If practical, provide an optional fully local Supabase-compatible development environment.

Podman must work where it supports Docker Compose compatibility.

Document both:

```text
docker compose
```

and, where applicable:

```text
podman compose
```

Do not require users to install both Docker and Podman.

---

# 51. Configuration

Create:

```text
.env.example
```

Example variables:

```text
APP_ENV=development
APP_URL=http://localhost:8000
SECRET_KEY=

DATABASE_URL=

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

SUPABASE_STORAGE_BUCKET=inventory-images

MAX_UPLOAD_SIZE=
IMAGE_MAX_DIMENSION=
THUMBNAIL_MAX_DIMENSION=
LABEL_DPI=203
```

Never commit actual credentials.

---

# 52. Security

The application contains information about possessions and potentially the physical organization of a private home.

Security is therefore important.

Implement:

- secure authentication;
- authorization on every protected endpoint;
- CSRF protection where applicable;
- XSS protection;
- SQL injection protection;
- secure cookies;
- security headers;
- Content Security Policy;
- upload validation;
- secret protection;
- rate limiting where appropriate;
- safe error handling.

Never expose:

```text
SUPABASE_SERVICE_ROLE_KEY
DATABASE_PASSWORD
SECRET_KEY
```

to client-side JavaScript.

Never log credentials or authentication tokens.

---

# 53. Content Security Policy

The application must have a restrictive CSP compatible with its frontend architecture.

Avoid inline scripts and inline styles where possible.

Prefer:

- external/static JavaScript;
- external/static CSS;
- nonces/hashes where inline code is unavoidable.

Do not weaken CSP merely to make a frontend implementation work.

---

# 54. Audit Information

Important mutations should record:

- user;
- timestamp;
- object;
- operation.

At minimum:

- item creation;
- item update;
- item deletion;
- item movement;
- image changes;
- access scope changes;
- user/permission changes.

A full audit log may be implemented as a future feature, but the data model should not prevent it.

---

# 55. Project Structure

Suggested structure:

```text
.
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── auth/
│   ├── users/
│   ├── access/
│   ├── items/
│   ├── categories/
│   ├── tags/
│   ├── locations/
│   ├── movements/
│   ├── relationships/
│   ├── media/
│   ├── qr/
│   ├── labels/
│   ├── search/
│   ├── backup/
│   ├── api/
│   ├── db/
│   └── common/
│
├── templates/
├── static/
├── migrations/
├── tests/
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
├── README.md
├── ARCHITECTURE.md
└── SPECIFICATION.md
```

The exact structure may be changed if a better architecture is justified.

---

# 56. Testing

Use:

- pytest;
- pytest-asyncio where necessary;
- Playwright for E2E tests where practical.

Test:

## Authentication

- login;
- logout;
- unauthorized access;
- role restrictions.

## Access Scopes

- matching item;
- non-matching item;
- multiple rules;
- permissions;
- user access changes;
- URL access bypass attempts.

## Items

- create;
- read;
- update;
- delete.

## Images

- valid upload;
- invalid upload;
- image optimization;
- thumbnail generation.

## QR

- generation;
- stable URL;
- invalid QR payload;
- unauthorized item access.

## Movements

- movement creation;
- location update;
- history;
- transaction rollback.

## Search

- name;
- UUID;
- tags;
- serial number;
- manufacturer;
- filters.

## Backup

- export;
- archive validation;
- import;
- invalid archive;
- broken references;
- schema version handling.

## PWA

- manifest;
- service worker;
- installability.

---

# 57. Performance

The application must remain responsive with thousands of inventory items.

Requirements:

- database pagination;
- indexed queries;
- optimized image sizes;
- thumbnails for list views;
- lazy loading where appropriate;
- no loading of all items into memory;
- efficient search;
- SQL aggregation for statistics.

Use optimized images in list/grid views.

Use full-resolution optimized images only on the item detail page.

---

# 58. Mobile UX

The application is expected to be used primarily from a smartphone.

Design mobile-first.

Important actions must be easy to reach:

```text
Search
Scan QR
Add item
Move item
Print label
```

Touch targets should be sufficiently large.

Forms should be optimized for mobile.

Avoid unnecessary multi-step navigation.

---

# 59. Desktop UX

Desktop should provide:

- keyboard-friendly navigation;
- larger item tables/grids;
- efficient search;
- bulk operations in future;
- drag-and-drop image upload;
- easy administration.

The application must remain responsive from approximately:

```text
360px
```

to large desktop displays.

---

# 60. Accessibility

Follow basic WCAG principles.

Implement:

- semantic HTML;
- labels for inputs;
- keyboard navigation;
- visible focus states;
- sufficient contrast;
- alt text for images;
- accessible dialogs;
- accessible error messages.

Do not rely exclusively on color to communicate state.

---

# 61. Development Method

The coding agent must work incrementally.

Do NOT generate the complete application in one operation.

For every phase:

1. inspect repository;
2. inspect current implementation;
3. read `SPECIFICATION.md`;
4. read `ARCHITECTURE.md`;
5. implement only the current phase;
6. add/update tests;
7. run formatter;
8. run static analysis;
9. run tests;
10. fix failures;
11. update documentation;
12. summarize changes;
13. stop.

Do not automatically proceed to the next phase.

---

# 62. Development Phases

## Phase 0 — Documentation and Architecture

Create:

```text
README.md
ARCHITECTURE.md
SPECIFICATION.md
.env.example
pyproject.toml
```

Document architecture and development workflow.

Do not implement application functionality yet.

---

## Phase 1 — Application Skeleton

Implement:

- FastAPI;
- Jinja2;
- static assets;
- Tailwind;
- configuration;
- logging;
- health endpoint;
- base layout;
- error handling.

---

## Phase 2 — Database

Implement:

- SQLAlchemy;
- PostgreSQL;
- Alembic;
- models;
- migrations;
- indexes;
- constraints.

---

## Phase 3 — Authentication and Users

Implement:

- Supabase Auth;
- login;
- logout;
- sessions;
- users;
- roles;
- administrator user management.

---

## Phase 4 — Categories, Tags and Locations

Implement CRUD and hierarchical structures.

---

## Phase 5 — Access Scopes

Implement:

- scopes;
- rules;
- permissions;
- user assignment;
- authorization engine;
- administration UI;
- scope preview/count.

This phase requires particularly careful testing.

---

## Phase 6 — Items

Implement:

- item model;
- CRUD;
- characteristics;
- item page;
- item editor.

---

## Phase 7 — Images

Implement:

- upload;
- optimization;
- thumbnails;
- Supabase Storage;
- gallery;
- primary image.

---

## Phase 8 — QR

Implement:

- UUID QR;
- QR generation;
- QR display;
- QR download;
- stable `/item/<uuid>` URLs.

---

## Phase 9 — QR Scanner

Implement:

- camera scanning;
- QR validation;
- item lookup;
- manual fallback.

---

## Phase 10 — Movement History

Implement:

- movement records;
- move workflow;
- timeline;
- authorization;
- transactional location changes.

---

## Phase 11 — Item Relationships

Implement:

- parent item;
- related items;
- relationship types.

---

## Phase 12 — Search

Implement:

- global search;
- filters;
- pagination;
- PostgreSQL optimization.

---

## Phase 13 — Thermal Labels

Implement:

- label size selector;
- label renderer;
- PNG generation;
- Web Share API;
- desktop download;
- print-friendly interface.

Do not implement printer-specific Bluetooth communication.

---

## Phase 14 — PWA

Implement:

- manifest;
- icons;
- service worker;
- standalone mode;
- installation UX.

---

## Phase 15 — Backup / Restore

Implement:

- export;
- ZIP archive;
- manifest;
- JSON files;
- images;
- validation;
- preview;
- import;
- rollback/error handling.

---

## Phase 16 — Security Hardening

Review:

- authentication;
- authorization;
- CSRF;
- CSP;
- XSS;
- uploads;
- cookies;
- secrets;
- rate limiting;
- headers;
- error handling.

---

## Phase 17 — Testing

Complete unit, integration and E2E tests.

---

## Phase 18 — Deployment

Deploy to Vercel.

Verify:

- environment variables;
- Supabase;
- database;
- storage;
- authentication;
- images;
- QR;
- labels;
- PWA;
- production URLs.

---

## Phase 19 — Final Review

Perform complete review:

```text
Architecture
Security
Database
Authorization
Access Scopes
Search
Images
QR
Movement history
Labels
PWA
Backup
Performance
Mobile UX
Accessibility
Tests
Documentation
Deployment
```

Fix all discovered issues.

---

# 63. Definition of Done

The MVP is complete only when:

- the application starts locally;
- Docker/Podman development environment works;
- PostgreSQL migrations work from an empty database;
- authentication works;
- administrators can manage users;
- roles work;
- Access Scopes work;
- unauthorized objects cannot be accessed;
- users can create items;
- users can edit permitted items;
- users can delete permitted items;
- images are optimized;
- thumbnails are generated;
- original uploads are not retained;
- QR codes work;
- QR scanning works;
- item URLs are stable;
- movement history works;
- locations work;
- categories work;
- tags work;
- relationships work;
- search works;
- label generation works;
- mobile sharing works where browser-supported;
- desktop PNG download works;
- PWA installation works;
- export works;
- import works;
- invalid archives are rejected safely;
- tests pass;
- static analysis passes;
- no secrets are committed;
- Vercel deployment works;
- README contains complete setup/deployment instructions.

---

# 64. Important Coding-Agent Instructions

You are an autonomous coding agent working on this repository.

Before changing anything:

1. inspect the repository;
2. read `SPECIFICATION.md`;
3. read `README.md`;
4. read `ARCHITECTURE.md` if it exists;
5. inspect existing migrations;
6. inspect existing tests.

Never assume functionality does not exist before searching the repository.

Do not create duplicate abstractions.

Do not rewrite working code without a clear reason.

Do not introduce dependencies without justification.

Do not change database schema without an Alembic migration.

Do not bypass authorization checks.

Do not implement security-sensitive functionality only on the frontend.

Do not store secrets in source code.

Do not store original uploaded images permanently.

Do not implement barcode functionality.

Do not implement printer-specific Bluetooth communication.

The label system must produce portable image files that can be shared to printer applications.

Do not make the application dependent on Vercel-specific business logic.

If Vercel's serverless execution model creates a limitation, adapt the architecture instead of introducing a persistent-server dependency.

Keep business logic portable.

When a requirement is ambiguous, choose the simplest secure implementation consistent with this specification and document the decision.

---

# 65. First Task for OpenCode

Start with **Phase 0 only**.

Create and configure the project documentation and basic development configuration.

At the end of Phase 0:

1. validate generated files;
2. run available formatting/static checks;
3. verify that documentation is internally consistent;
4. do not implement application functionality;
5. summarize what was created;
6. stop.

Do not proceed to Phase 1 automatically.

---

# 66. Future Features

The architecture should allow future implementation of:

- multi-property inventory;
- multiple houses;
- advanced RBAC;
- user groups;
- Access Scope templates;
- dynamic collections;
- bulk operations;
- CSV import/export;
- inventory reports;
- warranty tracking;
- maintenance history;
- purchase documents;
- receipts;
- depreciation;
- notifications;
- reminders;
- NFC tags;
- native mobile applications;
- offline mode;
- AI-assisted item recognition;
- OCR;
- automatic characteristic extraction;
- browser extension;
- public/shareable item pages with explicit permission;
- audit log;
- inventory analytics.

These features should NOT be implemented in the MVP unless explicitly requested.