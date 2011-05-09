# Installation directories
top_srcdir=..
localedir = $(RPM_BUILD_ROOT)/usr/share/locale

PGOAL = openclass

# perl files to search translatable strings in
PL_FILES = ../teacher.py ../student.py
# C-like files to search translatable strings in
#CFILES = 

POFILES = $(shell ls *.po)
MOFILES = $(POFILES:%.po=%.mo)
LANGS = $(POFILES:%.po=%)

PREFIX = $(RPM_BUILD_ROOT)/usr
DATADIR = $(PREFIX)/share
LOCALEDIR=$(DATADIR)/locale

GOALS = $(PGOAL).pot $(MOFILES)

all: $(GOALS)

install: all
	for l in $(LANGS); do \
		install -d $(localedir)/$$l/LC_MESSAGES; \
		install -m 644 $$l.mo $(localedir)/$$l/LC_MESSAGES/$(PGOAL).mo; \
	done

clean:
	rm -f *~ *.[oas] *.mo $(MOFILES) TAGS $(PL_CFILES)

%.mo: %.po
	msgfmt -o $@ $<

$(PGOAL).pot: $(PL_FILES)
	./pygettext.py -o $(PGOAL).pot $(PL_FILES)

update_n_merge: $(PGOAL).pot merge

merge:
	@for n in $(POFILES); do \
		echo "Merging $$n"; \
		msgmerge -C "$$n" "$$n" $(PGOAL).pot > "$$n"t; \
		mv -f "$$n"t "$$n"; \
	done

