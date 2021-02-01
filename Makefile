PIP := python -m pip --disable-pip-version-check


install-requirements:
	$(PIP) install -r requirements.txt

install-requirements-dev:
	$(PIP) install -r requirements_dev.txt

test:
	python -m pytest

build-dist:
	python setup.py sdist bdist_wheel

publish-test:
	python -m twine upload --repository testpypi dist/* --verbose

publish:
	python -m twine upload dist/*
