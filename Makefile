setup-uv:
	uv sync

start:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

call-endpoints:
	@echo "--- Calling API Endpoints ---"

	@echo "\n--- GET / (Root) ---"
	curl http://localhost:8001/

	@echo "\n--- GET /items/ (List all items) ---"
	curl http://localhost:8001/items/

	@echo "\n--- POST /items/ (Create a custom item via Query Params) ---"
	curl -X POST "http://localhost:8001/items/?name=My%20Custom%20Item&description=This%20is%20a%20custom%20item%20created%20via%20curl."

	@echo "\n--- GET /items/ (Check if the new item appears) ---"
	curl http://localhost:8001/items/

	@echo "\n--- GET /complex_operation/ ---"
	curl http://localhost:8001/complex_operation/

	@echo "\n--- All endpoints called ---"

.PHONY: all setup-uv fmt lint test clean run call-endpoints

lint:
	uv run python -m ruff check --fix app

sort-imports:
	uv run python -m isort app

fmt:
	uv run python -m black app

all: sort-imports fmt lint
up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose up --build

down-with-volumes:
	docker-compose down --volumes

clean:
	@echo "Cleaning up..."
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .ruff_cache
	rm -rf $(VENV_DIR)
	@echo "Cleanup complete."
