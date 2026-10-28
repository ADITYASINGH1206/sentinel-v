.PHONY: help dev stop test lint format parity bundle eval-all clean

help:
	@echo "SENTINEL-V Make Targets:"
	@echo "  make dev         - Start Docker Compose services (mock mode) + seed demo data"
	@echo "  make stop        - Stop all Docker Compose services"
	@echo "  make test        - Run unit and integration tests (mock mode)"
	@echo "  make lint        - Run linters (ruff, mypy, eslint, forbidden copy)"
	@echo "  make format      - Format code (ruff format, prettier)"
	@echo "  make parity      - Run parity checks against S-MSDT upstream (GPU required)"
	@echo "  make bundle      - Build an immutable model bundle from checkpoint"
	@echo "  make eval-all    - Execute Paper B evaluation harness (E1 through E12)"
	@echo "  make clean       - Clean temporary build artifacts and test caches"

dev:
	docker compose -f infra/compose.yaml up -d --build
	@echo "Waiting for services to become healthy..."
	@sleep 5
	python3 scripts/dev_seed.py || true
	@echo "SENTINEL-V is running:"
	@echo "  Console: http://localhost:5173"
	@echo "  API:     http://localhost:8080/docs"

stop:
	docker compose -f infra/compose.yaml down

test:
	pytest packages/ services/ -v -m "not gpu"

lint:
	ruff check packages/ services/ tools/
	mypy packages/ services/
	python3 tools/check_no_metric_literals.py web/src services/

format:
	ruff format packages/ services/ tools/

parity:
	python3 tools/parity_check.py --config eval/configs/parity.yaml

bundle:
	@if [ -z "$(CKPT)" ] || [ -z "$(VARIANT)" ] || [ -z "$(VAL_SCORES)" ]; then \
		echo "Usage: make bundle CKPT=path.pt VARIANT=st VAL_SCORES=val.csv [OUT=models/bundle-...]"; exit 1; \
	fi
	python3 tools/make_bundle.py --ckpt $(CKPT) --variant $(VARIANT) --val-scores $(VAL_SCORES) --out $(or $(OUT),models/bundle-latest)

eval-%:
	python3 eval/scripts/run_experiment.py --id $*

eval-all:
	python3 eval/scripts/run_all.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf dist build *.egg-info
