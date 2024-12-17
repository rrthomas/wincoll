# Makefile for maintainer tasks

po/wincoll.pot: po/wincoll.pot.in
	sed -e s/VERSION/$$(grep version pyproject.toml | grep -o "[0-9.]\+")/ < $^ > $@

update-pot:
	$(MAKE) po/wincoll.pot
	find wincoll -name "*.py" | xargs xgettext --from-code=utf-8 --default-domain=wincoll --output=po/wincoll.pot

update-po:
	for po in po/*.po; do msgmerge --update $$po po/wincoll.pot; done

compile-po:
	for po in po/*.po; do mo=wincoll/locale/$$(basename $${po%.po})/LC_MESSAGES/wincoll.mo; mkdir -p $$(dirname $$mo); msgfmt --output-file=$$mo $$po; done
	for po in po-argparse/*.po; do mo=wincoll/locale/$$(basename $${po%.po})/LC_MESSAGES/argparse.mo; mkdir -p $$(dirname $$mo); msgfmt --output-file=$$mo $$po; done

build:
	$(MAKE) update-pot
	$(MAKE) update-po
	$(MAKE) compile-po
	python -m build

dist:
	git diff --exit-code && \
	rm -rf ./dist && \
	mkdir dist && \
	$(MAKE) build

test:
	tox

release:
	make test
	make dist
	twine upload dist/* && \
	git tag v$$(grep version pyproject.toml | grep -o "[0-9.]\+") && \
	git push --tags

.PHONY: dist build
