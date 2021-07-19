PYTHON=python3

ifdef PREFIX
PREFIX_ARG=--prefix=$(PREFIX)
endif

all: build

build:
	$(PYTHON) setup.py build

clean:
	-$(PYTHON) setup.py clean --all
	find . -name '*.py[cdo]' -exec rm -f '{}' ';'
	rm -rf __pycache__ dist build htmlcov
	rm -f README.md MANIFEST *,cover .coverage

install: build
	$(PYTHON) setup.py install $(PREFIX_ARG)

dist:
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*

upload: dist
	$(PYTHON) -m twine upload dist/*

tests:
	@echo "There aren't any tests yet!" >& 2 && exit 1

coverage: tests

black:
	black dogslow_sentry tests setup.py

pyflakes:
	pyflakes dogslow_sentry setup.py

pylint:
	pylint --rcfile=.pylintrc dogslow_sentry setup.py

.PHONY: all build clean install dist tests coverage pep8 pyflakes pylint \
	upload
