BIN_DIR      := artifacts/bin
BIN          := $(BIN_DIR)/ipcrawler
LOG_DIR      := artifacts/logs
RUN_DIR      := artifacts/runs
PROFILE      ?= release
RUN_ARGS     ?=

.PHONY: help build build-prod run clean fmt clippy check tools verify

help:
	@echo "Targets:"
	@echo "  make build                        - Build $(BIN) (release) + create system symlink + install config"
	@echo "  make build-prod                   - Build $(BIN) (production)"
	@echo "  make run RUN_ARGS=\"-v -t host\"     - Run with args"
	@echo "  make clean                        - Clean build + remove system symlink"
	@echo "  make tools                        - Install/verify external tools locally"
	@echo "  make verify                       - Verify env and folder writability"
	@echo "  make fmt | make clippy | check    - Format, lint, tests"

build:
	@mkdir -p $(BIN_DIR) $(LOG_DIR) $(RUN_DIR)
	@cargo build --release
	@cp -f target/release/ipcrawler $(BIN)
	@echo "Built $(BIN) (release)"
	@echo "Creating local symlink: ~/.local/bin/ipcrawler -> $(PWD)/$(BIN)"
	@mkdir -p ~/.local/bin
	@rm -f ~/.local/bin/ipcrawler
	@ln -sf $(PWD)/$(BIN) ~/.local/bin/ipcrawler
	@echo "Installing global config: ~/.config/ipcrawler/global.toml"
	@mkdir -p ~/.config/ipcrawler
	@cp -f global.toml ~/.config/ipcrawler/global.toml
	@echo "✅ ipcrawler command now available (add ~/.local/bin to PATH if needed)"

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
	@echo "Removing local symlink: ~/.local/bin/ipcrawler"
	@rm -f ~/.local/bin/ipcrawler
	@echo "Removing user config: ~/.config/ipcrawler/"
	@rm -rf ~/.config/ipcrawler

# Swallow incidental phony goals if user passes flags directly
%:
	@: