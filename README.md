# pg-user-api 🐘

A lightweight **Flask REST API** for managing PostgreSQL user accounts across
multiple environments (dev, qa, uat, prod).  
Built for teams that provision database roles repeatedly and want a simple,
auditable HTTP interface instead of manual `psql` commands.

---

## ✨ Features

| Feature | Details |
|---|---|
| **HTTP Basic Auth** | Every `/api/*` endpoint is protected |
| **SQLite inventory** | Databases registered by env + name — no static config files |
| **Audit log** | Every operation is recorded in SQLite |
| **Multi-environment** | dev / qa / uat / prod with separate hostnames per database |
| **Structured JSON** | Responses include hostname, database, port, env, status |
| **Notification stubs** | Placeholders for Webex, Slack, and email hooks |
| **Postgres-only** | Purpose-built for PostgreSQL / AWS RDS |

---

## 📁 Project Layout

```
pg_user_api/
├── app.py              # Flask application — all endpoints
├── auth.py             # Basic auth helper (constant-time compare)
├── database.py         # SQLite registry + audit log
├── notifications.py    # Notification stubs (email / Webex / Slack)
├── seed_db.py          # One-time setup: creates DB + sample records
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/pg-user-api.git
cd pg-user-api
pip install -r requirements.txt
```

### 2. Seed the SQLite registry

```bash
python seed_db.py
```

This creates `pg_registry.db` and inserts sample records for dev / qa / uat / prod.
Edit `seed_db.py` and replace the `SAMPLE_RECORDS` list with your real PostgreSQL hostnames.

### 3. Set credentials

The API has two credential pairs — set them as environment variables before starting:

```powershell
# Windows PowerShell
$env:PG_API_USER   = "pgadmin"          # who can call this API
$env:PG_API_PASS   = "Ch@ngeMe2024!"
$env:PG_ADMIN_USER = "role_create"      # PostgreSQL DBA role that executes DDL
$env:PG_ADMIN_PASS = "your_pg_password"
```

```bash
# Linux / macOS
export PG_API_USER="pgadmin"
export PG_API_PASS="Ch@ngeMe2024!"
export PG_ADMIN_USER="role_create"
export PG_ADMIN_PASS="your_pg_password"
```

If you don't set env vars, the defaults coded in `app.py` are used.

### 4. Start the API

```bash
python app.py
```

The API listens on `http://localhost:5000`.

---

## 🗃 SQLite Registry: Adding Databases

The inventory lives in the `db_registry` table of `pg_registry.db`.

### Schema

| Column   | Type    | Description                          |
|----------|---------|--------------------------------------|
| env      | TEXT    | `dev` / `qa` / `uat` / `prod`        |
| db_name  | TEXT    | PostgreSQL database name             |
| hostname | TEXT    | FQDN or IP of the PostgreSQL host    |
| port     | INTEGER | PostgreSQL port (default 5432)       |
| active   | INTEGER | `1` = active, `0` = inactive         |
| notes    | TEXT    | Free-text description                |

### Insert records

```bash
sqlite3 pg_registry.db
```

```sql
INSERT INTO db_registry (env, db_name, hostname, port, active, notes)
VALUES
  ('dev',  'myapp_dev',  'pg-dev-01.example.com',  5432, 1, 'Dev main DB'),
  ('qa',   'myapp_qa',   'pg-qa-01.example.com',   5432, 1, 'QA main DB'),
  ('uat',  'myapp_uat',  'pg-uat-01.example.com',  5432, 1, 'UAT main DB'),
  ('prod', 'myapp_prod', 'pg-prod-01.example.com', 5432, 1, 'Production DB');
```

### Deactivate a database

```sql
UPDATE db_registry SET active = 0
WHERE env = 'dev' AND db_name = 'myapp_dev';
```

---

## 🔐 Authentication

All `/api/*` endpoints require **HTTP Basic Auth**.

```bash
curl -u pgadmin:Ch@ngeMe2024! http://localhost:5000/api/v1/registry
```

An unauthenticated request returns `401 Unauthorized`.

---

## 📡 API Endpoints

All endpoints use **GET** with query parameters.  
The DBA credentials are stored server-side — callers only need `env` and `database`
plus the user-specific fields shown below.

### Response format

Every user operation returns:

```json
{
  "username": "web01_8080",
  "password": "generatedSecurePassword",
  "status":   "user created",
  "hostname": "pg-dev-01.example.com",
  "database": "myapp_dev",
  "port":     "5432",
  "env":      "dev"
}
```

---

### `GET /` — Health check

```bash
curl http://localhost:5000/
```

---

### `GET /api/v1/registry` — List registered databases

```bash
curl -u pgadmin:Ch@ngeMe2024! "http://localhost:5000/api/v1/registry"
```

---

### `GET /api/v1/users/all` — List all PostgreSQL roles

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/all?env=dev&database=myapp_dev"
```

---

### `GET /api/v1/users/app` — Create application user `<servername>_<port>`

Typical use: VM or container service accounts.

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/app?env=dev&database=myapp_dev&servername=web01&port=8080"
```

Creates user `web01_8080` with connection limit 200.

---

### `GET /api/v1/users/app-k8s` — Create Kubernetes workload user `<env_prefix>_<farmname>`

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/app-k8s?env=dev&database=myapp_dev&env_prefix=dv&farmname=gearservice"
```

Creates user `dv_gearservice` with connection limit 200.

---

### `GET /api/v1/users/devqa` — Create dev/QA individual user

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/devqa?env=dev&database=myapp_dev&username=jsmith"
```

Creates user `jsmith` with connection limit 20.

---

### `GET /api/v1/users/devlead` — Create dev-lead user

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/devlead?env=qa&database=myapp_qa&username=jdoe"
```

Creates user `jdoe` with connection limit 20.

---

### `GET /api/v1/users/readonly` — Create read-only user

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/readonly?env=prod&database=myapp_prod&username=analyst01"
```

Creates user `analyst01` with connection limit 20.

---

### `GET /api/v1/users/dba` — Create DBA user

Creates user with `CREATEDB CREATEROLE LOGIN`.

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/dba?env=dev&database=myapp_dev&username=dba_alice"
```

---

### `GET /api/v1/users/reset` — Reset a user's password

Generates a new random password and applies it immediately.

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/reset?env=dev&database=myapp_dev&username=jsmith"
```

---

### `GET /api/v1/users/search-path` — Update search_path

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/search-path?env=dev&database=myapp_dev&username=jsmith&schema=public"
```

`schema` defaults to `public` if not supplied.

---

### `GET /api/v1/users/find` — Look up a specific user

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/find?env=dev&database=myapp_dev&username=jsmith"
```

---

## 🧪 Testing Before You Use It

Before running against a real database, follow these steps to verify everything works.

### 1. Check the API is running

```bash
curl http://localhost:5000/
```

Expected response:
```json
{"service": "PostgreSQL User Management API", "version": "2.0.0", ...}
```

### 2. Verify your registry has the database registered

```bash
curl -u pgadmin:Ch@ngeMe2024! "http://localhost:5000/api/v1/registry"
```

If your `env` + `database` combination is not listed, add it first:

```bash
sqlite3 pg_registry.db
```
```sql
INSERT INTO db_registry (env, db_name, hostname, port, active, notes)
VALUES ('qa', 'myapp_qa', 'pg-qa-01.example.com', 5432, 1, 'QA main DB');
```

### 3. List existing users on the target database

Run this first before any create operation — confirms connectivity and shows
what already exists:

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/all?env=qa&database=myapp_qa"
```

If this returns a user list, your DBA credentials and network connectivity are good.
If it errors, check `PG_ADMIN_USER` / `PG_ADMIN_PASS` and that the host is reachable.

### 4. Test user creation

Create a test user first to confirm the full flow works end to end:

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/devqa?env=qa&database=myapp_qa&username=test_api_user"
```

Expected response:
```json
{
  "username": "test_api_user",
  "password": "<generated>",
  "status":   "user created",
  "hostname": "pg-qa-01.example.com",
  "database": "myapp_qa",
  "port":     "5432",
  "env":      "qa"
}
```

### 5. Verify the user was created

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/find?env=qa&database=myapp_qa&username=test_api_user"
```

### 6. Test password reset

```bash
curl -u pgadmin:Ch@ngeMe2024! \
  "http://localhost:5000/api/v1/users/reset?env=qa&database=myapp_qa&username=test_api_user"
```

### 7. Check the audit log

Every operation is recorded in SQLite. Verify your test actions were logged:

```bash
sqlite3 pg_registry.db "SELECT * FROM audit_log ORDER BY performed_at DESC LIMIT 10;"
```

### Common errors

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong API username/password | Check `PG_API_USER` / `PG_API_PASS` |
| `No registry entry found` | Database not in SQLite | Add it via `seed_db.py` or `sqlite3` |
| `password authentication failed` | Wrong DBA credentials | Check `PG_ADMIN_USER` / `PG_ADMIN_PASS` |
| `could not connect to server` | Host unreachable | Check hostname in registry, VPN, firewall |
| `user already exists` | Username taken | Normal — the API is idempotent, no action taken |

---

## 📊 Quick Reference

| Endpoint | Required params | Creates |
|---|---|---|
| `/api/v1/users/all` | `env`, `database` | — lists users |
| `/api/v1/users/app` | `env`, `database`, `servername`, `port` | `<servername>_<port>` |
| `/api/v1/users/app-k8s` | `env`, `database`, `env_prefix`, `farmname` | `<env_prefix>_<farmname>` |
| `/api/v1/users/devqa` | `env`, `database`, `username` | individual dev/QA user |
| `/api/v1/users/devlead` | `env`, `database`, `username` | individual dev-lead user |
| `/api/v1/users/readonly` | `env`, `database`, `username` | read-only user |
| `/api/v1/users/dba` | `env`, `database`, `username` | DBA user (CREATEDB+CREATEROLE) |
| `/api/v1/users/reset` | `env`, `database`, `username` | — resets password |
| `/api/v1/users/search-path` | `env`, `database`, `username`, `schema` | — updates search_path |
| `/api/v1/users/find` | `env`, `database`, `username` | — looks up user |

---

## 📬 Notifications (Webex / Slack / Email)

`notifications.py` contains ready-to-activate stubs. Uncomment the relevant
block and add your token/webhook URL:

```python
# Webex Teams
send_notification(
    channel="webex",
    recipient="YOUR_WEBEX_ROOM_ID",
    message="User {} created on {} ({})".format(username, dbname, env),
)

# Slack
send_notification(
    channel="slack",
    message="User {} created on {} ({})".format(username, dbname, env),
)

# Email
send_notification(
    channel="email",
    recipient="dba-team@example.com",
    message="User {} created on {} ({})".format(username, dbname, env),
)
```

---

## 🛡 Security Notes

- Intended for **internal / intranet** use behind a VPN or firewall.
- The DBA credentials are stored server-side and never appear in API URLs or logs.
- Never commit `pg_registry.db` to a public repository — it contains hostnames.
  It is already listed in `.gitignore`.
- For internet-facing deployments, upgrade to token-based auth (JWT / API key).

---

## 📝 License

MIT — free to use, modify, and share.
