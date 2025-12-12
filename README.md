# BBB Class Monitor

A lightweight Python server that lists active BigBlueButton meetings and exposes quick links to join or end a meeting. Credentials and API settings are read from environment variables (recommended via a local `.env` file).

## Requirements
- Python 3.11+
- `pip install -r requirements.txt`

## Local setup
1. Create your environment file:
   - Copy `sample.env` to `.env`.
   - Fill in real values for `API_URL`, `API_SECRET`, `USERNAME`, and `PASSWORD`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the monitor:
   ```bash
   python bbb_monitor.py
   ```
   The server starts on `SERVER_PORT` (default `8000`).

## Docker
- Build:
  ```bash
  docker build -t bbb-monitor .
  ```
- Run (using your `.env`):
  ```bash
  docker run --rm -p 8000:8000 --env-file .env bbb-monitor
  ```
- Visit `http://localhost:8000/` and log in with `USERNAME`/`PASSWORD` from your env.

## Environment Variables
- `API_URL` (required): BigBlueButton API base URL (e.g., `https://bbb.example.com/bigbluebutton/api`).
- `API_SECRET` (required): BigBlueButton shared secret.
- `SERVER_PORT` (optional): HTTP port to serve the monitor (default `8000`).
- `REFRESH_INTERVAL_SECONDS` (optional): Polling interval for updates (default `15`).
- `USERNAME` (required): Basic auth username for accessing the monitor page.
- `PASSWORD` (required): Basic auth password for accessing the monitor page.

Sensitive values are read from the environment and not printed to stdout. Use `.env` only for local development; set environment variables directly in production or container environments.
