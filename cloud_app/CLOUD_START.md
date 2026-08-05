# Cardio Vita Cloud Start

This file is the first practical checklist for moving the local clinic app to cloud hosting.

## Current Local App

Local URL:

```text
http://127.0.0.1:18081
```

Project folder:

```text
/Users/user/Documents/Bshkuhi project/cloud_app
```

Current local database:

```text
/Users/user/Documents/Bshkuhi project/cloud_app/data/clinic.sqlite
```

## Stage 1: Test Before Cloud

Use fake patients first.

1. Login as admin.
2. Create one patient in Տերյան and one patient in Նարեկացի.
3. Confirm automatic anketa numbers are separate:
   - Տերյան: `T-000001`, `T-000002`, ...
   - Նարեկացի: `N-000001`, `N-000002`, ...
4. In Ժամադրություններ, search a patient by name, surname, passport, and phone.
5. Create appointments for both branches.
6. Try to create duplicate same doctor/date/time and confirm it is blocked.
7. In Ծառայություններ:
   - choose Ընդհանուր and confirm service list changes by doctor specialty.
   - choose Լաբորատոր and confirm all doctors can refer lab tests.
8. Add Holter record and print Holter answer.
9. Login as doctor and check:
   - patient search
   - գանգատներ
   - ախտորոշում
   - document type dropdown
   - print document
10. Login as staff user for each branch and confirm branch isolation.
11. Check dashboard numbers as admin.
12. Click Ելք and confirm logout works.

## Stage 2: Choose Cloud

Recommended first setup:

- App host: Render
- Database: Supabase Postgres or Neon Postgres

The clinic data should not be stored only inside the web server container. It should be in managed Postgres with backups.

## Stage 3: Supabase Database

In Supabase:

1. Open your Supabase project.
2. Go to Project Settings -> Database.
3. Copy the Postgres connection string.
   - Prefer the pooled connection string for hosted apps.
   - Keep the password/private URL secret.
3. Open SQL editor.
4. Run the single full setup file:

```text
scripts/supabase_full_setup.sql
```

Alternative: run schema and seed separately:

```text
scripts/postgres_schema.sql
```

```text
scripts/seed_clinic_users_doctors.sql
```

6. Keep the connection string private.

## Stage 4: Export Local Data From SQLite

Run from this folder:

```bash
python3 scripts/export_sqlite_to_json.py
```

It creates a timestamped JSON export under:

```text
backups/
```

This is the safest first migration file. We can import it into Postgres after the cloud database is created.

## Stage 5: Import Export Into Supabase

Install dependencies once:

```bash
python3 -m pip install -r requirements.txt
```

Then run:

```bash
DATABASE_URL='postgresql://...' python3 scripts/import_json_to_postgres.py backups/clinic_export_YYYYMMDD_HHMMSS.json
```

Replace `postgresql://...` with the Supabase connection string and replace the JSON filename with the newest export.

## Stage 6: App Database Mode

The backend now supports both local SQLite and cloud Postgres:

```text
without DATABASE_URL -> local SQLite
with DATABASE_URL    -> Supabase/Render Postgres
```

Environment variables:

```text
APP_ENV=production
APP_SECRET=<long random secret>
ADMIN_PASSWORD=<strong temporary admin password>
DATABASE_URL=<postgres connection string>
COOKIE_SECURE=true
```

## Stage 7: Render Free Test

1. Push the `cloud_app` folder to GitHub.
2. In Render, create a new Web Service from that repository.
3. If Render asks for root directory, choose:

```text
cloud_app
```

4. Use Docker runtime or the included `render.yaml`.
5. Add these environment variables:

```text
APP_ENV=production
COOKIE_SECURE=true
DATABASE_URL=<Supabase pooled connection string>
ADMIN_PASSWORD=<temporary strong password>
APP_SECRET=<long random secret, or let Render generate it>
```

Render free is okay for testing. It may sleep when nobody uses it, so the first open can be slow.

## Security Notes

- Do not use the default admin password in production.
- Use HTTPS only.
- Create separate users for each staff member and doctor.
- Do not share one login between branches.
- Keep daily database backups enabled in Supabase/Neon.
- Limit admin access to one or two trusted people.
