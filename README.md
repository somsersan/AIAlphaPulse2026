# AI Alpha Pulse

See `PRODUCT_SPEC.md` for the full specification and `ROADMAP.md` for the plan.

## Database setup

AI Alpha Pulse uses PostgreSQL 14+ with async SQLAlchemy (`asyncpg` driver).

### 1. Create the database and user

Run the following in `psql` as a superuser (e.g. `psql -U postgres`):

```sql
CREATE USER aialpha WITH PASSWORD 'change_me';
CREATE DATABASE aialpha OWNER aialpha;
GRANT ALL PRIVILEGES ON DATABASE aialpha TO aialpha;
```

### 2. Configure environment

Copy the template and fill in your credentials:

```bash
cp .env.example .env
# then edit DATABASE_URL, e.g.:
# DATABASE_URL=postgresql+asyncpg://aialpha:change_me@localhost:5432/aialpha
```

`.env` is git-ignored; only `.env.example` is committed.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply migrations

```bash
alembic upgrade head
```

To create a new migration after editing models:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

### 5. Verify the connection

```bash
python scripts/check_db.py
```

Expected output: `OK`. Any other output indicates a configuration or
connectivity issue (the full error is printed to stderr).
