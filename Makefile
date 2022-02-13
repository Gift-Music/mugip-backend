.PHONY: all
all:


.PHONY: update_requirements
update_requirements:
	pip-compile --generate-hashes --no-header -o requirements.txt setup.py
	pip-compile --no-header -o requirements-dev.txt requirements-dev.in

.PHONY: reset_test_env
reset_test_env:
	python scripts/reset_test_env.py