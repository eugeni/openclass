from distutils.core import setup
from distutils.filelist import findall

import py2exe
import glob
import os

DESTDIR="win_dist"

setup(
        windows = [
            {
                "script": 'student.py',
                "icon_resources": [(0, "iface/student.ico")]
            },
            {
                "script": 'teacher.py',
                "icon_resources": [(0, "iface/teacher.ico")]
            }
        ],
        options = {
            'py2exe':
                {
                    "includes": "pango,cairo,pangocairo,atk,gobject,gio",
                    "dist_dir": DESTDIR,
                },
                },
            data_files = [
            ("iface", ["iface/machine.png", "iface/machine_off.png", "iface/openclass.png"]),
        ],
        zipfile = None,
        )

# cleanup
os.chdir(DESTDIR)
#os.system("rmdir /s /q tcl")
#os.system("del /s /q *tcl* *tkinter*")
