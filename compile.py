from distutils.core import setup
from distutils.filelist import findall

import py2exe
import glob
import os

DESTDIR="win_dist"

setup(
        console=['student.py', 'teacher.py'],
        options = {
            'py2exe':
                {
                    "includes": "pango,cairo,pangocairo,atk,gobject,gio",
                    "dist_dir": DESTDIR,
                },
                },
            data_files = [
            ("iface", glob.glob("iface/*")),
	    ],
        zipfile = "lib.dat",
        )

# cleanup
os.chdir(DESTDIR)
#os.system("rmdir /s /q tcl")
#os.system("del /s /q *tcl* *tkinter*")
