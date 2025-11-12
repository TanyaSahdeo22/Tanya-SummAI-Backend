# Tanya-SummAI-Backend

This repository contains a small FastAPI backend that provides a WebSocket-based collaborative editing backend and a minimal REST endpoint.

## What this project provides

- WebSocket endpoint: `/ws/{file_id}` — collaborative editing socket for a given file id.
- REST endpoint: `GET /files` — lists in-memory files and metadata.
- Interactive API docs: `/docs` (provided by FastAPI when the server is running).

## Prerequisites

- Python 3.9+ (a virtual environment is recommended)


## Quick setup (recommended)

1. Create and activate a virtual environment (recommended):

```bash
# from project root
python3 -m venv .venv
source .venv/bin/activate
```

If `python3` points to a different version, adjust accordingly (e.g. `python3.10`).

2. Install dependencies

```bash
# after activating venv
pip install -r requirements.txt
# if uvicorn is not in requirements, you can install it explicitly
pip install uvicorn
```

3. Run the server

```bash
# recommended (uses uvicorn installed in venv)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# alternative (explicit venv python)
.venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- The server will be available at `http://127.0.0.1:8000` (or on your machine's IP when using `0.0.0.0`).
- Visit `http://127.0.0.1:8000/docs` for interactive API docs.
- `GET /files` returns the current in-memory files metadata.

