# Makefile for maintainer tasks

po/wincoll.pot: po/wincoll.pot.in
	sed -e s/VERSION/$$(grep version pyproject.toml | grep -o "[0-9.]\+")/ < $^ > $@

update-pot:
	$(MAKE) po/wincoll.pot
	find wincoll -name "*.py" | xargs xgettext --add-comments=TRANSLATORS --from-code=utf-8 --default-domain=wincoll --output=po/wincoll.pot.in

update-po:
	rm -f po/*.po
	wget --recursive --level=1 --no-directories \
			--accept=po --directory-prefix=po --no-verbose \
			https://translationproject.org/latest/wincoll/

compile-po:
	for po in po/*.po; do mo=wincoll/locale/$$(basename $${po%.po})/LC_MESSAGES/wincoll.mo; mkdir -p $$(dirname $$mo); msgfmt --output-file=$$mo $$po; done

update-pofiles:
	$(MAKE) update-pot
	$(MAKE) po/wincoll.pot
	$(MAKE) update-po
	$(MAKE) compile-po

build:
	$(MAKE) update-pofiles
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

loc:
	cloc --exclude-content="ptext module" wincoll/*.py

.PHONY: dist build
