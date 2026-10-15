# SoleStyle

SoleStyle is a responsive footwear storefront and in-store reservation manager. Customers browse real product and size/color inventory, reserve pairs, track booking status and receive saved notifications. Staff handle inventory, customers and reservations from a protected admin area.

**Reservations only:** there is no checkout payment, payment gateway, shipping, home delivery or delivery tracking. A reservation is not a sale. Customers visit the physical shop to try on, collect or purchase their pair.

## Features

- Responsive storefront, search, category/brand/size/color/price filters, sorting and product details.
- Customer registration and password-hashed sign-in, saved cart, wishlist, profile and booking history.
- Size/color variant stock, transactional reservation creation, stock release on cancellation and unique booking IDs.
- Persistent notifications with live Flask-SocketIO updates while a customer is connected.
- Role-protected admin dashboard, product/stock management, reservation status changes, customer access control, CSV exports and shop settings.
- CSRF protection, secure session cookie defaults, file type and size validation, parameterized ORM queries.
- Local SQLite fallback for quick setup; MySQL 8+ supported for deployment.

## Quick start (Windows PowerShell)

From this folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
flask --app app init-db
flask --app app create-admin
flask --app app run --debug
```

Open http://127.0.0.1:5000. The local database and uploads live under `instance/`. The initializer creates a small catalog and common categories/brands so the storefront can be previewed immediately; replace that catalog with real inventory from the admin dashboard.

On macOS/Linux, activate the environment with `source .venv/bin/activate`; the remaining commands are the same.

## PostgreSQL setup

For a free hosted database, Neon currently offers a free tier suitable for prototypes (1 GB storage and 100 compute-hours per project). It scales to zero after five idle minutes, so its first connection after idle can be slower. Create a Neon project in the region closest to the Render service, copy its pooled connection string, and add it as `DATABASE_URL` in the Render service environment. Use the `postgresql://` connection string; the application converts it to the psycopg SQLAlchemy dialect. Never commit the connection string.

The Render Blueprint leaves `DATABASE_URL` unsynced so Render asks for the external secret during setup. The previously created Render free database is separate and is not used by this configuration.

## MySQL setup

Create a dedicated MySQL database and user, grant the user access only to that database, then set `DATABASE_URL` in `.env`:

```env
DATABASE_URL=mysql+pymysql://sole_user:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:3306/sole_style?charset=utf8mb4
SECRET_KEY=replace-with-a-long-random-secret
FLASK_DEBUG=0
COOKIE_SECURE=1
```

Use a long randomly generated `SECRET_KEY`; URL-encode special characters in the database password. The SQL reference is in `database/schema.sql`; normally `flask --app app init-db` creates tables and inserts taxonomy/seed records through SQLAlchemy. Create the first administrator securely with `flask --app app create-admin`; this command asks for the credentials locally and refuses to create a second bootstrap administrator.

For a production server, serve over HTTPS, keep `.env` and `instance/` private, back up MySQL and uploaded images, use a production WSGI/Socket.IO deployment (for example Gunicorn with an appropriate Socket.IO worker), and set `COOKIE_SECURE=1`. Do not expose Flask's debug server to the internet.

## Routes

- Customer: `/`, `/products`, `/login`, `/register`, `/cart`, `/booking/confirm`, `/my-bookings`, `/dashboard`, `/wishlist`, `/notifications`, `/profile`.
- Admin (admin role required): `/admin`, `/admin/products`, `/admin/bookings`, `/admin/customers`, `/admin/reports`, `/admin/settings`.

## Operational notes

- Customers can cancel while a booking is pending or confirmed. The admin may transition bookings through Pending Confirmation, Confirmed, Ready for Pickup, Completed and Cancelled. Cancellation returns stock; reopening a cancelled reservation rechecks stock.
- Inventory is decremented when a reservation is created. A cancelled reservation releases its stock. Completed booking value is not reported as revenue.
- Password reset currently provides a safe shop-assisted path. Add a verified email provider and expiring, single-use reset tokens before enabling email self-service.
- Customer ratings, recommendations and aggregate review content are not captured by this minimal schema; the storefront labels are illustrative design content and should be replaced with verified store reviews before launch.
- Product variants are administered through comma-separated size and color lists with one starting stock value applied to newly added combinations. Use a dedicated stock adjustment workflow for an established catalog.
- Uploaded product images are limited to JPG, PNG and WebP and an 8 MB request cap. The uploads folder must be backed up with the database.

## Database reference

The normalized MySQL schema is provided at `database/schema.sql`. SQLAlchemy models in `app.py` define the running schema, including users, categories, brands, products, variants, cart, wishlist, bookings, booking items, notifications, activity and shop settings.
