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

import sys
import os
import socket
import traceback
import struct
import SocketServer
import time

import tempfile

import logging

def get_user_name():
    """Returns current user name"""
    if get_os() == "Linux":
        return os.getenv("USER")
    else:
        return os.getenv("USERNAME")

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
        return os.startfile(url)

def shutdown():
    """Shuts down the machine"""
    if get_os() == "Linux":
        # shutdown
        return os.system("poweroff")
    else:
        # TODO: no shutdown yet on windows
        return os.system("shutdown -s -t 01 -c \"Shutting down per teacher request\"")

def get_client_id():
    """Returns client id (if any)"""
    if get_os() == "Linux":
        client_id = os.getenv("DISPLAY")
    else:
        # TODO: get proper client id
        client_id = ""
    return client_id

def create_tmp_file(suffix=''):
    """Creates a temporary file"""
    fd, tmpfile = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return tmpfile

def get_home():
    """Returns user homedir"""
    if get_os() == "Linux":
        return os.getenv("HOME")
    else:
        return os.getenv("HOMEPATH")

def setup_logger(log_name):
    """Configures the logger"""
    log_file="%s%s%s.log" % (get_home(), os.sep, log_name)
    logger = logging.getLogger("openclass_teacher")
    h1 = logging.FileHandler(log_file)
    f = logging.Formatter("%(levelname)s %(asctime)s: %(funcName)s+%(lineno)d: %(message)s")
    h1.setFormatter(f)
    h1.setLevel(logging.DEBUG)
    h2 = logging.StreamHandler(sys.stdout)
    h2.setFormatter(f)
    h2.setLevel(logging.DEBUG)
    logger.addHandler(h1)
    logger.addHandler(h2)
    logger.setLevel(logging.DEBUG)
    return logger
