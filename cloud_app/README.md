# Cardio Vita Clinic App

Two-branch clinic register for Տերյան and Նարեկացի.

## What Is Included

- Login/session authentication
- Admin and branch staff roles
- Admin-only dashboard with clinic metrics
- Patients, appointments, services, Holter records
- Weekly doctor calendar
- Branch working-hour validation
- Duplicate protection: the same doctor cannot be booked at the same date/time in either branch
- Branch-scoped data access for staff users
- SQLite database for low-cost hosting
- JSON export for admin users
- Docker, health check, Nginx example, and backup script

## Working Hours

- Տերյան: Monday-Friday 08:00-20:00, Saturday-Sunday 10:00-18:00
- Նարեկացի: Monday-Friday 08:00-20:00, Saturday 09:00-18:00, Sunday closed
- From 18:00 to 20:00 the calendar uses 10-minute slots; before 18:00 it uses 30-minute slots.

## Local Run

```bash
python3 server.py
```

Open:

```text
http://127.0.0.1:8080
```

In Codex it is currently started on:

```text
http://127.0.0.1:18081
```

First local login:

```text
username: admin
password: ChangeMe2026!
```

## Production Setup

For the cloud migration checklist, Postgres schema, and data export steps, see:

```text
CLOUD_START.md
```

1. Copy `.env.example` to `.env`.
2. Set strong values for `APP_SECRET` and `ADMIN_PASSWORD`.
3. Keep `APP_ENV=production` and `COOKIE_SECURE=true`.
4. Run with Docker Compose:

```bash
docker compose up -d --build
```

5. Put Nginx in front of the app and enable HTTPS with Let's Encrypt.
6. Replace `clinic.example.com` in `deploy/nginx.conf` with the real domain.

## Backup

Manual backup:

```bash
APP_DIR=/path/to/cloud_app CLINIC_DB=/path/to/cloud_app/data/clinic.sqlite ./scripts/backup.sh
```

On a VPS, run the backup script daily with cron. Backups are kept for 30 days by default.

## Security Notes

- Do not use the default admin password for real patient data.
- Use separate staff users for each branch.
- Staff users only see/write their own branch.
- Admin users can see both branches, manage users, view dashboard, and export JSON backup.
- Host only through HTTPS in real use.
- Keep SSH access restricted and update the server regularly.
