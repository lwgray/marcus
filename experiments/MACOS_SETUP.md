# macOS Setup Guide for PM Agent Experiments

## PostgreSQL Driver Issues on macOS

If you encounter the error:
```
ImportError: dlopen(.../_psycopg.cpython-311-darwin.so, 0x0002): symbol not found in flat namespace '_PQbackendPID'
```

### Solution 1: Use psycopg2-binary (Recommended)

```bash
# Uninstall the source version
pip uninstall psycopg2

# Install the binary version
pip install psycopg2-binary
```

### Solution 2: Install PostgreSQL and link libraries

```bash
# Install PostgreSQL via Homebrew
brew install postgresql

# Export PostgreSQL library path
export LDFLAGS="-L/opt/homebrew/opt/postgresql/lib"
export CPPFLAGS="-I/opt/homebrew/opt/postgresql/include"

# Reinstall psycopg2
pip uninstall psycopg2
pip install psycopg2 --no-binary psycopg2
```

### Solution 3: Use SQLite (Default)

The setup script now automatically falls back to SQLite if PostgreSQL fails. No action needed!

## Quick Start

```bash
# 1. Install dependencies (with psycopg2-binary)
pip install -r requirements.txt

# 2. Run setup (will use SQLite by default)
python scripts/setup_experiments.py

# 3. To force PostgreSQL (optional)
export DATABASE_URL="postgresql://user:pass@localhost/pmexperiments"
python scripts/setup_experiments.py
```

## Verify Installation

```bash
# Test database connection
python -c "from sqlalchemy import create_engine; engine = create_engine('sqlite:///experiments.db'); print('SQLite OK')"

# Test with PostgreSQL (if needed)
python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://localhost/test'); print('PostgreSQL OK')"
```