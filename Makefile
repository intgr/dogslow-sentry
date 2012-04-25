PYTHON=python

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
	TAR_OPTIONS="--owner=root --group=root --mode=u+w,go-w,a+rX-s" \
	$(PYTHON) setup.py -q sdist

upload: dist
	$(PYTHON) setup.py upload

tests:
	@echo "There aren't any tests yet!" >& 2 && exit 1

coverage: tests

# E261: two spaces before inline comment
# E301: expected blank line
# E302: two new lines between functions/etc.
pep8:
	pep8 --ignore=E261,E301,E302 --repeat dogslow setup.py

pyflakes:
	pyflakes dogslow setup.py

pylint:
	pylint --rcfile=.pylintrc dogslow setup.py

.PHONY: all build clean install dist tests coverage pep8 pyflakes pylint \
	upload
