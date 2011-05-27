from distutils.core import setup
from distutils.filelist import findall

import py2exe
import glob
import os

DESTDIR="win_dist"

# {{{ gtkfiles
gtkfiles = [ \
    ("etc", [  ]),
    ("etc/gtk-2.0", [ "distfiles/etc/gtk-2.0/gdk-pixbuf.loaders", "distfiles/etc/gtk-2.0/gtk.immodules", "distfiles/etc/gtk-2.0/gtkrc", "distfiles/etc/gtk-2.0/im-multipress.conf" ]),
    ("etc/pango", [ "distfiles/etc/pango/pango.aliases", "distfiles/etc/pango/pango.modules" ]),
    ("lib", [ "distfiles/lib/charset.alias" ]),
    ("lib/gtk-2.0", [  ]),
    ("lib/gtk-2.0/2.10.0", [  ]),
    ("lib/gtk-2.0/2.10.0/engines", [ "distfiles/lib/gtk-2.0/2.10.0/engines/libpixmap.dll", "distfiles/lib/gtk-2.0/2.10.0/engines/libsvg.dll", "distfiles/lib/gtk-2.0/2.10.0/engines/libwimp.dll" ]),
    ("lib/gtk-2.0/2.10.0/immodules", [ "distfiles/lib/gtk-2.0/2.10.0/immodules/im-am-et.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-cedilla.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-cyrillic-translit.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-ime.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-inuktitut.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-ipa.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-multipress.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-thai.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-ti-er.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-ti-et.dll", "distfiles/lib/gtk-2.0/2.10.0/immodules/im-viqr.dll" ]),
    ("lib/gtk-2.0/2.10.0/loaders", [ "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-ani.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-bmp.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-gif.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-ico.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-jpeg.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-pcx.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-png.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-pnm.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-ras.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-tga.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-tiff.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-wbmp.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-xbm.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/libpixbufloader-xpm.dll", "distfiles/lib/gtk-2.0/2.10.0/loaders/svg_loader.dll" ]),
    ("lib/libglade", [  ]),
    ("lib/libglade/2.0", [  ]),
    ("lib/pango", [  ]),
    ("lib/pango/1.6.0", [  ]),
    ("lib/pango/1.6.0/modules", [ "distfiles/lib/pango/1.6.0/modules/pango-arabic-fc.dll", "distfiles/lib/pango/1.6.0/modules/pango-arabic-lang.dll", "distfiles/lib/pango/1.6.0/modules/pango-basic-fc.dll", "distfiles/lib/pango/1.6.0/modules/pango-basic-win32.dll", "distfiles/lib/pango/1.6.0/modules/pango-hangul-fc.dll", "distfiles/lib/pango/1.6.0/modules/pango-hebrew-fc.dll", "distfiles/lib/pango/1.6.0/modules/pango-indic-fc.dll", "distfiles/lib/pango/1.6.0/modules/pango-indic-lang.dll", "distfiles/lib/pango/1.6.0/modules/pango-khmer-fc.dll", "distfiles/lib/pango/1.6.0/modules/pango-syriac-fc.dll", "distfiles/lib/pango/1.6.0/modules/pango-thai-fc.dll", "distfiles/lib/pango/1.6.0/modules/pango-tibetan-fc.dll" ]),
    ("share", [  ]),
    ("share/themes", [  ]),
    ("share/themes/MS-Windows", [  ]),
    ("share/themes/MS-Windows/gtk-2.0", [ "distfiles/share/themes/MS-Windows/gtk-2.0/gtkrc" ]),
    ("share/xml", [  ]),
    ("share/xml/libglade", [ "distfiles/share/xml/libglade/glade-2.0.dtd" ]),
]
# }}}

setup(
        console=['student.py', 'teacher.py'],
        options = {
            'py2exe':
                {
                    "includes": "pango,cairo,pangocairo,atk,gobject,gio",
                    "dist_dir": DESTDIR,
                },
                },
            data_files = gtkfiles + [
            ("iface", glob.glob("iface/*")),
	    ],
        zipfile = "lib.dat",
        )

# cleanup
os.chdir(DESTDIR)
#os.system("rmdir /s /q tcl")
#os.system("del /s /q *tcl* *tkinter*")
