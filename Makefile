PACKAGE = openclass
VERSION = 0.2

version:
	echo "version='$(VERSION)'" > version.py

install:
	mkdir -p $(DESTDIR)/usr/share/openclass
	mkdir -p $(DESTDIR)/usr/bin
	install -m755 openclass-teacher $(DESTDIR)/usr/bin/openclass-teacher
	install -m755 openclass-student $(DESTDIR)/usr/bin/openclass-student
	cp -a teacher.py student.py iface openclass $(DESTDIR)/usr/share/openclass/
	# locale
	$(MAKE) -C po $@
	# desktop
	mkdir -p $(DESTDIR)/usr/share/applications/
	install -m644 openclass-teacher.desktop $(DESTDIR)/usr/share/applications/
	install -m644 openclass-student.desktop $(DESTDIR)/usr/share/applications/

cleandist:
	rm -rf $(PACKAGE)-$(VERSION) $(PACKAGE)-$(VERSION).tar.bz2

tar:
	tar cfj $(PACKAGE)-$(VERSION).tar.bz2 $(PACKAGE)-$(VERSION)
	rm -rf $(PACKAGE)-$(VERSION)

gitdist: cleandist
	git archive --prefix $(PACKAGE)-$(VERSION)/ HEAD | bzip2 -9 > $(PACKAGE)-$(VERSION).tar.bz2
