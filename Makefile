# Find version
VERSION := $(shell grep --color=never VERSION ChangeLog | head -1 | sed -e "s/VERSION //;s/ .*//")

all: prepare

.PHONY: all prepare reset FORCE

%.py: Makefile ChangeLog FORCE
	@sed -i -r "s:(^ *version[[:space:]]+=[[:space:]]')[^']*('.*):\1${VERSION}\2:g" $@

prepare: setup.py confmgr/confmgr.py
	python setup.py sdist
	make reset

clean:
	@rm -rfv build dist

reset: setup.py confmgr/confmgr.py
reset: VERSION := "@VERSION@"