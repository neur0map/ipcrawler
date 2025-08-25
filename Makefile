BIN_DIR      := artifacts/bin
BIN          := $(BIN_DIR)/ipcrawler
LOG_DIR      := artifacts/logs
RUN_DIR      := artifacts/runs
PROFILE      ?= release
RUN_ARGS     ?=

.PHONY: help build build-prod run clean fmt clippy check tools verify

help:
	@echo "Targets:"
	@echo "  make build                        - Build $(BIN) (dev)"
	@echo "  make build-prod                   - Build $(BIN) (production)"
	@echo "  make run RUN_ARGS=\"-v -t host\"     - Run with args"
	@echo "  make tools                        - Install/verify external tools locally"
	@echo "  make verify                       - Verify env and folder writability"
	@echo "  make fmt | make clippy | check    - Format, lint, tests"

build:
	@mkdir -p $(BIN_DIR) $(LOG_DIR) $(RUN_DIR)
	@cargo build
	@cp -f target/debug/ipcrawler $(BIN)
	@echo "Built $(BIN) (dev)"

build-prod:
	@mkdir -p $(BIN_DIR) $(LOG_DIR) $(RUN_DIR)
	@cargo build --release
	@cp -f target/release/ipcrawler $(BIN)
	@echo "Built $(BIN) (production)"

run: build
	@./scripts/run.sh $(RUN_ARGS)

tools:
	@bash scripts/install_tools.sh

verify:
	@bash scripts/check_tools.sh
	@mkdir -p $(RUN_DIR) $(LOG_DIR) && touch $(LOG_DIR)/.write && rm $(LOG_DIR)/.write
	@echo "Environment verified."

fmt:
	cargo fmt --all

clippy:
	cargo clippy -- -D warnings

check:
	cargo test

clean:
	cargo clean
	rm -rf artifacts/

# Swallow incidental phony goals if user passes flags directly
%:
	@: