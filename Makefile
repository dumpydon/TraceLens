.PHONY: install dev backend lab-checkout lab-payment frontend test lint ingest traffic eval

install:
	python3 -m venv .venv
	.venv/bin/pip install -e 'backend[dev]'
	cd frontend && npm install

backend:
	PYTHONPATH=backend:. .venv/bin/uvicorn app.main:app --reload --port 8000

lab-checkout:
	.venv/bin/uvicorn incident_lab.checkout_service.main:app --port 8101

lab-payment:
	.venv/bin/uvicorn incident_lab.payment_service.main:app --port 8102

frontend:
	cd frontend && npm run dev

test:
	.venv/bin/pytest backend/tests
	cd frontend && npm test

lint:
	.venv/bin/ruff check backend incident_lab evaluation
	cd frontend && npm run lint

ingest:
	.venv/bin/python -m app.rag.ingest

traffic:
	.venv/bin/python -m incident_lab.scenarios traffic --count 12

eval:
	PYTHONPATH=backend:. .venv/bin/python evaluation/run_eval.py
