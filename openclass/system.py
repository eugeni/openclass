#!/usr/bin/python
"""OpenClass system module

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.
"""

import os
import socket
import traceback
import struct
import SocketServer
import time

def get_user_name():
    """Returns current user name"""
    if get_os() == "Linux":
        return os.getenv("USER")
    else:
        return "user"

def get_os():
    """Returns the name of the OS"""
    try:
        # quick workaround - windows has no 'uname' :)
        ret = os.uname()
        return "Linux"
    except:
        return "Windows"

def timefunc():
    # TODO: if windows, return time.clock(); otherwise return time.time()
    return time.time()

def open_url(url):
    """Attempts to open an url"""
    if get_os() == "Linux":
        return os.system("xdg-open '%s' &" % url)
    else:
        # TODO: make it work on windows
        return os.system(url)

def shutdown():
    """Shuts down the machine"""
    if get_os() == "Linux":
        # shutdown
        return os.system("shutdown now")
    else:
        # TODO: no shutdown yet on windows
        return None
