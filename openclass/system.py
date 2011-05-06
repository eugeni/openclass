#!/usr/bin/python
"""OpenClass system module"""

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
