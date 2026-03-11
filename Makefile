.PHONY= clean clean-test clean-pyc clean-all install test dist release-test release
PIP := python -m pip --disable-pip-version-check
INSTALL_FILE ?= requirements-dev.txt
INTALL_LOG ?= /dev/stdout

test:
	tox

install:
	pip install -r $(INSTALLF_ILE) 2>&1 > $(INSTALL_LOG)
	pip freeze

clean:
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info

clean-test:
	@rm -rf .coverage coverage*
	@rm -rf .pytest_cache/

clean-pyc:
	-@find . -name '*.pyc' -not -path "./.tox/*" -follow -print0 | xargs -0 rm -f
	-@find . -name '*.pyo' -not -path "./.tox/*" -follow -print0 | xargs -0 rm -f
	-@find . -name '__pycache__' -type d -not -path "./.tox/*" -follow -print0 | xargs -0 rm -rf

clean-all: clean-test clean-pyc
	@rm -rf .tox/
	@rm -rf .mypy_cache/

dist: clean
	python -m build
	ls -l dist
	python -m twine check dist/*

release-test: clean dist
	python -m twine upload --repository testpypi dist/* --verbose

release: clean dist
	python -m twine upload dist/*
