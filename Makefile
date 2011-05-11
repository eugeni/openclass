PACKAGE = openclass
VERSION = 0.0.1

version:
	echo "version='$(VERSION)'" > version.py

install:
	mkdir -p $(RPM_BUILD_ROOT)/usr/share/openclass
	mkdir -p $(RPM_BUILD_ROOT)/usr/bin
	install -m755 openclass-teacher $(RPM_BUILD_ROOT)/usr/bin/openclass-teacher
	install -m755 openclass-student $(RPM_BUILD_ROOT)/usr/bin/openclass-student
	cp -a teacher.py student.py iface openclass $(RPM_BUILD_ROOT)/usr/share/openclass/
	# locale
	$(MAKE) -C po $@
	# desktop
	mkdir -p $(RPM_BUILD_ROOT)/usr/share/applications/
	install -m644 openclass-teacher.desktop $(RPM_BUILD_ROOT)/usr/share/applications/
	install -m644 openclass-student.desktop $(RPM_BUILD_ROOT)/usr/share/applications/

cleandist:
	rm -rf $(PACKAGE)-$(VERSION) $(PACKAGE)-$(VERSION).tar.bz2

tar:
	tar cfj $(PACKAGE)-$(VERSION).tar.bz2 $(PACKAGE)-$(VERSION)
	rm -rf $(PACKAGE)-$(VERSION)

gitdist: cleandist
	git archive --prefix $(PACKAGE)-$(VERSION)/ HEAD | bzip2 -9 > $(PACKAGE)-$(VERSION).tar.bz2
