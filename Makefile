# Makefile
# Usage:
#   make all
#   make tools
#   make bcc
#   make docker
#   make check
#   make venv

SHELL := /bin/bash

.PHONY: all tools bcc docker check venv

all: tools bcc docker venv

tools:
	sudo apt update
	sudo apt install -y \
	  linux-tools-$$(uname -r) \
	  linux-cloud-tools-$$(uname -r) \
	  linux-tools-generic \
	  linux-cloud-tools-generic

bcc:
	sudo apt update
	sudo apt install -y bpfcc-tools python3-bpfcc

docker:
	sudo apt update
	sudo apt install -y docker.io
	sudo systemctl enable docker
	sudo systemctl start docker
	sudo usermod -aG docker $$USER
	@echo "Added $$USER to docker group."
	@echo "Log out and log back in, or run: newgrp docker"

venv:
	cd /home/test/eBeeMetrics/lib/latencies && \
	python3 -m venv venv && \
	venv/bin/python -m pip install --upgrade pip && \
	venv/bin/python -m pip install numpy matplotlib pandas scikit-learn

check:
	@echo "Kernel: $$(uname -r)"
	@echo -n "docker: " && (docker --version || echo "NOT INSTALLED")
	@echo -n "bcc tools: " && (dpkg -s bpfcc-tools >/dev/null 2>&1 && echo "OK" || echo "NOT INSTALLED")
	@echo -n "python bpfcc: " && (python3 -c "import bcc; print('OK')" 2>/dev/null || echo "NOT INSTALLED")
	@echo -n "docker group: " && (groups $$USER | grep -q docker && echo "OK" || echo "LOG OUT/LOG IN REQUIRED")