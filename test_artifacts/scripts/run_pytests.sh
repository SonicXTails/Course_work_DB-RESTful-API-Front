
#!/usr/bin/env bash
set -e
export API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
mkdir -p reports
pytest -q
