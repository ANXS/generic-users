.PHONY: bootstrap lint unit test-unit test test-all test-debian12 test-debian13 test-ubuntu2004 test-ubuntu2204 test-ubuntu2404 act-lint act-test clean distclean

VENV := .venv
BIN := $(VENV)/bin
STAMP := $(VENV)/.installed
export PATH := $(CURDIR)/$(BIN):$(PATH)

$(STAMP): requirements-dev.txt
	python3 -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements-dev.txt
	@touch $(STAMP)

bootstrap: $(STAMP)

lint: $(STAMP)
	$(BIN)/yamllint -c .yamllint .github collections.yml defaults meta molecule requirements.yml tasks
	$(BIN)/ansible-lint -c .ansible-lint defaults meta tasks

test-unit: $(STAMP)
	$(BIN)/pytest -q tests/unit

unit: test-unit

test: lint test-unit test-all

test-debian12: $(STAMP)
	MOLECULE_OS=debian MOLECULE_VERSION=12 \
		MOLECULE_IMAGE=geerlingguy/docker-debian12-ansible:latest \
		$(BIN)/molecule test

test-debian13: $(STAMP)
	MOLECULE_OS=debian MOLECULE_VERSION=13 \
		MOLECULE_IMAGE=geerlingguy/docker-debian13-ansible:latest \
		$(BIN)/molecule test

test-ubuntu2004: $(STAMP)
	MOLECULE_OS=ubuntu MOLECULE_VERSION=2004 \
		MOLECULE_IMAGE=geerlingguy/docker-ubuntu2004-ansible:latest \
		$(BIN)/molecule test

test-ubuntu2204: $(STAMP)
	MOLECULE_OS=ubuntu MOLECULE_VERSION=2204 \
		MOLECULE_IMAGE=geerlingguy/docker-ubuntu2204-ansible:latest \
		$(BIN)/molecule test

test-ubuntu2404: $(STAMP)
	MOLECULE_OS=ubuntu MOLECULE_VERSION=2404 \
		MOLECULE_IMAGE=geerlingguy/docker-ubuntu2404-ansible:latest \
		$(BIN)/molecule test

test-all: test-debian12 test-debian13 test-ubuntu2004 test-ubuntu2204 test-ubuntu2404

act-lint:
	act -j lint

act-test:
	act -j test

clean:
	@if [ -x "$(BIN)/molecule" ]; then $(BIN)/molecule destroy; fi

distclean: clean
	rm -rf $(VENV) .cache .pytest_cache

