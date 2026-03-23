.PHONY: up stop down logs run status restart

up:
	docker-compose up -d

stop:
	docker-compose stop

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

run:
	uv run python scripts/run.py

status:
	@echo "=== Docker services ==="
	@docker-compose ps
	@echo ""
	@echo "=== Ollama models ==="
	@docker-compose exec ollama ollama list 2>/dev/null || echo "Ollama not running"
	@echo ""
	@echo "=== DB tables ==="
	@docker-compose exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "\dt" 2>/dev/null || echo "DB not accessible"