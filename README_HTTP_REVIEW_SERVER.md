# HTTP review server

`streamlit_app.py` remains the interactive local dashboard. `http_review_server.py`
is a separate read-only companion for environments that cannot execute
Streamlit's browser JavaScript/WebSocket client.

Start it on a second local port:

```bash
.venv/bin/python3 http_review_server.py --port 8506
```

Open `http://127.0.0.1:8506/`. The server renders ordinary HTML pages and
provides direct CSV and JSON endpoints for the Phase 11 clinical tables and the
Exploratory Empirical Findings phase.

For a temporary Cloudflare tunnel, keep the HTTP server bound to localhost and
run this in a second terminal:

```bash
cloudflared tunnel --url http://127.0.0.1:8506
```

The HTTP server hides patient identifier columns in its HTML pages by default.
The CSV files are still direct downloads of the stored outputs. Do not expose
the server publicly unless the data have been approved for external sharing.

Optional token protection can be enabled before starting the server:

```bash
HTTP_REVIEW_TOKEN='use-a-long-random-token' .venv/bin/python3 http_review_server.py --port 8506
```

Then provide the token as an `X-Review-Token` header or as `?token=...` when
accessing a page. For a durable deployment with patient data, use an
authenticated named Cloudflare Tunnel or an institutional reverse proxy rather
than a quick tunnel.
