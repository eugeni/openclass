#!/usr/bin/python
"""This file describes the communication protocol of OpenClass.

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

OPENCLASS_HEADER="Open Class"
OPENCLASS_VERSION_MAJOR=0
OPENCLASS_VERSION_MINOR=1
OPENCLASS_BUILD=1

# protocol commands
ACTION_NOOP="noop"
# message from teacher
ACTION_MSG="msg"
# attention
ACTION_ATTENTION="attention"
# full-screen projection
ACTION_PROJECTION="projection"
# ask for screen shot
ACTION_SHOT="shot"
# students needs to register again
ACTION_PLEASEREGISTER="pleaseregister"
# open a file from teacher
ACTION_OPENFILE="openfile"
# open an url from teacher
ACTION_OPENURL="openurl"
# shut down the machine
ACTION_SHUTDOWN="shutdown"

# requests
REQUEST_REGISTER="register"
REQUEST_ACTIONS="actions"
REQUEST_RAISEHAND="raisehand"
REQUEST_SHOWSCREEN="showscreen"
REQUEST_GETFILE="getfile"

import struct
import traceback

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
        header += struct.pack("!64p", class_name)
        flags = 0
        if restricted:
            flags |= ANNOUNCE_RESTRICTED
        header += struct.pack("i", flags)
        return header

    def parse_announce(self, announce):
        """Parses a class announcment"""
        try:
            name, flags = struct.unpack("!64pi", announce)
            # TODO: strip trailing null bytes
            return (name, flags)
        except:
            traceback.print_exc()
            return None

    def pack_chunk(self, screen_width, screen_height, fullscreen, chunk):
        """Packs a chunk into network-specific format for sending"""
        # TODO: instead of passing fullscreen as an integer, use Flags-like structure
        pos_x, pos_y, step_x, step_y, img = chunk
        data = struct.pack("!iiiiiii", screen_width, screen_height, fullscreen, pos_x, pos_y, step_x, step_y)
        return data + img

    def unpack_chunk(self, data):
        """Unpacks a chunk of data"""
        head_size = struct.calcsize("!iiiiiii")
        screen_width, screen_height, fullscreen, pos_x, pos_y, step_x, step_y = struct.unpack("!iiiiiii", data[:head_size])
        return screen_width, screen_height, fullscreen, pos_x, pos_y, step_x, step_y, data[head_size:]

