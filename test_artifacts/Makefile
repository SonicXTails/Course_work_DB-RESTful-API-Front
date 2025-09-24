
.PHONY: test smoke load restore

test:
	bash scripts/run_pytests.sh

smoke:
	locust -f load/locustfile.py --host $${API_BASE_URL:-http://localhost:8000} --headless -u 10 -r 5 -t 2m

load:
	locust -f load/locustfile.py --host $${API_BASE_URL:-http://localhost:8000} --headless -u 150 -r 20 -t 20m

restore:
	bash resilience/resilience_test.sh
