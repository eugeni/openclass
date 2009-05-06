#!/usr/bin/python
"""This file describes the communication protocol of OpenClass."""

OPENCLASS_HEADER="Open Class"
OPENCLASS_VERSION_MAJOR=0
OPENCLASS_VERSION_MINOR=1
OPENCLASS_BUILD=1

import struct

class Protocol:
    """This is the main class for OpenClass protocol."""
    # protocol commands
    COMMAND_ANNOUNCE=1
    # class announce flags
    ANNOUNCE_RESTRICTED = 1<<0

    def __init__(self):
        """Initializes protocol processing class"""
        # protocol messages
        self.header = struct.pack("!10sii", OPENCLASS_HEADER, OPENCLASS_VERSION_MAJOR, OPENCLASS_VERSION_MINOR)
        self.header_len = len(self.header)

    def parse_header(self, msg):
        """Parses header"""
        if len(msg) < self.header_len:
            # message too short
            print "Message too short"
            return None
        header = msg[:self.header_len]
        name, major, minor = struct.unpack("!10sii", header)
        if name != OPENCLASS_HEADER:
            # wrong app name
            print "Wrong app name: <%s|%s>" % (name, OPENCLASS_HEADER)
            return None
        if major != OPENCLASS_VERSION_MAJOR or minor != OPENCLASS_VERSION_MINOR:
            # bad version
            print "Wrong app version"
            return None
        # all ok
        return msg[self.header_len:]

    def create_announce(self, class_name, restricted=False):
        """Creates announce message."""
        header = self.header
        header += struct.pack("128s", class_name)
        flags = 0
        if restricted:
            flags |= ANNOUNCE_RESTRICTED
        header += struct.pack("!i", flags)
        return header

    def parse_announce(self, announce):
        """Parses a class announcment"""
        print announce


proto = Protocol()
a = proto.create_announce("hi")
print "<%s>" % a

msg = proto.parse_header(a)
print msg

print proto.parse_announce(msg)
