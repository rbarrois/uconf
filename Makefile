# Find version
VERSION := $(shell grep -m 1 --color=never "^VERSION" ChangeLog | head -1 | sed -e "s/VERSION //;s/ .*//")
COMMIT:=$(shell git log -n 1 | head -1 | sed -r 's/commit (.{8}).*/\1/')
DATE:=$(shell grep -m 1 --color=never "^VERSION" ChangeLog | sed -e 's/VERSION [^ ]\+ *//')

ifeq (${DATE},XX XX XXXX)
	VERSION:=${VERSION}_${COMMIT}
endif

all: prepare

.PHONY: all prepare clean test

%.py: Makefile ChangeLog
	@sed -i -r "s:(^ *version[[:space:]]+=[[:space:]]')[^']*('.*):\1${VERSION}\2:g" $@

prepare: setup.py confmgr/core.py
	rm -f dist/*.tar.gz
	python setup.py sdist
	git checkout $^

clean:
	@rm -rfv build dist

test:
	pychecker confmgr/*.py
