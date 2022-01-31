.PHONY: site clean watch watch-pandoc watch-browser-sync haddock

theme := escience
theme_dir := .entangled/templates/$(theme)

pandoc_args += -s -t html5 -f commonmark_x --toc --toc-depth 2
pandoc_args += --template $(theme_dir)/template.html
pandoc_args += --css theme.css
pandoc_args += --mathjax
# pandoc_args += --syntax-definition .entangled/syntax/dhall.xml
# pandoc_args += --highlight-style $(theme_dir)/syntax.theme
pandoc_args += --section-divs
pandoc_args += --lua-filter .entangled/scripts/hide.lua
pandoc_args += --lua-filter .entangled/scripts/annotate.lua
pandoc_args += --lua-filter .entangled/scripts/make.lua
pandoc_input := README.md $(wildcard lit/*.md)
pandoc_output := docs/index.html

static_files := $(theme_dir)/theme.css $(theme_dir)/static
static_targets := $(static_files:$(theme_dir)/%=docs/%)
functional_deps := Makefile $(wildcard .entangled/scripts/*.lua) $(theme_dir)/template.html $(theme_dir)/syntax.theme

site: $(pandoc_output) $(static_targets) $(figure_targets)

clean:
	rm -rf docs

$(static_targets): docs/%: $(theme_dir)/%
	@mkdir -p $(@D)
	rm -rf $@
	cp -r $< $@

docs/index.html: $(pandoc_input) $(functional_deps)
	@mkdir -p $(@D)
	pandoc $(pandoc_args) -o $@ $(pandoc_input)

# Starts a tmux with Entangled, Browser-sync and an Inotify loop for running
# Pandoc.
watch:
	@tmux new-session make --no-print-directory watch-pandoc \; \
		split-window -v make --no-print-directory watch-browser-sync \; \
		split-window -v entangled daemon \; \
		select-layout even-vertical \;

watch-pandoc:
	@while true; do \
		inotifywait -e close_write -r .entangled Makefile README.md; \
		make site; \
	done

watch-browser-sync:
	browser-sync start -w -s docs

