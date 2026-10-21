# RentSpace — Production Role Workflow

## Roles

### House Owner
After login:
1. Owner & Rental Information
2. Live Activity

No Dashboard menu.

### Tenant
After login:
1. Personal & Rental Information
2. Live Activity

No Dashboard menu.

Tenant Live Activity contains:
- Matched rental spaces
- Scheduled visits
- Allocated property
- Confirmed property
- Current scheduled visit
- My Details
- Edit My Details
- Confirmed-property feedback

Tenant edits generate Admin notifications.

### Admin
After login:
1. Dashboard
2. Managements
3. Live Activity
4. Notifications

No notification popup.

## Admin notifications

New notifications appear first. Marked-read notifications remain in history.

Notification messages include timestamp, HID/TID, name, and activity, for example:

`03 Oct 2026, 07:30 PM — H0003 - Dhanu entered as new house owner.`

`04 Oct 2026, 08:00 AM — H0003 - Dhanu updated rent.`

`06 Sep 2026, 12:30 PM — T0015 - Raja entered as new tenant.`

`15 Sep 2026, 02:15 PM — T0015 - Raja updated purpose of relocation.`

## IDs

Properties receive sequential HID values:
- H0001
- H0002
- H0003

Tenant profiles receive sequential TID values:
- T0001
- T0002
- T0003

## Run

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python run.py
```

Open:

`http://127.0.0.1:8000`

Demo accounts:
- Admin: `admin@rentspace.local` / `Admin@12345`
- Owner: `owner@rentspace.local` / `Owner@12345`
- Tenant: `tenant@rentspace.local` / `Tenant@12345`

## File upload security

Tenant Aadhar card upload accepts:
- PDF
- JPG
- JPEG
- DOCX

Files are stored under private uploads and are served through an Admin-authenticated route.

## Database persistence (important)

- **Local development:** if `DATABASE_URL` is omitted, RentSpace stores data in `instance/rentspace.db`. The file remains after app restarts, as long as you keep the project folder and database file.
- **Hosted production:** configure `DATABASE_URL` to a **persistent managed PostgreSQL** database. The included `render.yaml` defines a Render PostgreSQL database and connects it to the web service. Deploy using Render Blueprint support, then confirm the `DATABASE_URL` environment variable is set in the web service.
- Do not rely on SQLite inside a serverless or temporary deployment filesystem (including typical Vercel function storage). Data may disappear on redeploy/restart. Production mode deliberately refuses to start if `DATABASE_URL` is missing, rather than silently storing user data in temporary SQLite.
- Keep database credentials private. Never commit a real production connection string into `.env.example` or source control. Back up the managed database regularly.
- Existing data in a local SQLite database is **not automatically copied** to PostgreSQL. Migrate/export it separately if needed.

`ensure_schema()` adds forward-compatible columns to the configured database. For major schema changes, use database migrations and take a backup first.

## Admin table corrections
- Admin Live Activity groups owner and tenant fields in a single Live Status column, with each field shown on its own row and saved individually.
- Management tables show separate editable columns for admin-managed activity values.
- Active/Inactive is the only content shown in each management Status cell.
- View and Edit are separate actions. View is read-only and displays all available personal/profile and property columns; Edit provides editable personal/rental fields and a Save changes action.
- Management table cell spacing has been increased for readability.

Run locally from this directory with `python -m pip install -r requirements.txt` and `python run.py`.
