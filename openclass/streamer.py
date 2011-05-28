#!/usr/bin/python
"""Optimistic streaming module

This class provides an implementation of a data streamer for data
transmission over unreliable connections

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

import traceback
import struct
import os

STREAMER_PROTOCOL_VERSION=1
DEFAULT_CHUNK_SIZE=1024

class StreamerEncoder:
    #
    # protocol format:
    #  "OST" +
    #   protocol version(byte, big endian) +
    #   filename size(byte, big endian) +
    #   file name +
    #   size of chunk(unsigned short int, big endian) +
    #   number of chunks(unsigned long, big endian) +
    #   chunk id(unsigned long, big endian) +
    #   data

    def __init__(self, filename, chunk_size=DEFAULT_CHUNK_SIZE):
        """Initializes streamer"""
        self.chunk_size = chunk_size
        self.filename = filename
        self.short_filename = os.path.basename(filename)
        self.short_filename_len = len(self.short_filename)
        self.filesize = -1
        self.num_chunks = -1
        self.chunks = []
        self.fd = -1

    def prepare(self):
        """Prepares the file for transmission, returns total number of chunks"""
        try:
            fd = open(self.filename, "rb")
            fd.seek(0, 2)
            self.filesize = fd.tell()
            self.num_chunks = self.filesize / self.chunk_size
            if self.filesize / self.chunk_size != 0:
                self.num_chunks += 1
        except:
            traceback.print_exc()
            return False
        self.fd = fd
        return True

    def get_num_chunks(self):
        """Returns the number of chunks in file"""
        return self.num_chunks

    def get_chunk(self, pos):
        """Returns the encoded chunk corresponding to the offset in file"""
        try:
            self.fd.seek(self.chunk_size * pos)
            data = self.fd.read(self.chunk_size)
            return self.encode_chunk(pos, data)
        except:
            traceback.print_exc()
            return None

    def get_chunks(self, chunks=[]):
        """Returns a series of chunks, read at once. Returns a dict mapping chunk ids with file contents"""
        # sort the chunks
        chunks.sort()
        res = {}
        for chunk in chunks:
            res[chunk] = self.get_chunk(chunk)
        return res

    def encode_chunk(self, pos, data):
        """Encodes a chunk into streaming format"""
        res = "OST" + struct.pack("!BB", STREAMER_PROTOCOL_VERSION, self.short_filename_len) + \
            self.short_filename + \
            struct.pack("!HLL", self.chunk_size, self.num_chunks, pos) + \
            data
        return res

    def finish(self):
        """Finishes streaming"""
        self.fd.close()
        self.fd = None

class StreamerDecoder:
    #
    # protocol format:
    #  "OST" +
    #   protocol version(byte, big endian) +
    #   filename size(byte, big endian) +
    #   file name +
    #   size of chunk(unsigned short int, big endian) +
    #   number of chunks(unsigned long, big endian) +
    #   chunk id(unsigned long, big endian) +
    #   data

    def __init__(self, filename):
        """Initializes streamer"""
        self.filename = filename
        self.short_filename = os.path.basename(filename)
        self.short_filename_len = len(self.short_filename)
        self.fd = -1

        # calculate file parameters
        self.prepare()

    def prepare(self):
        """Prepares the file for transmission, returns total number of chunks"""
        try:
            fd = open(self.filename, "wb")
        except:
            traceback.print_exc()
            return False
        self.fd = fd
        return True

    def decode_chunk(self, chunk):
        """Decodes a chunk"""
        header = chunk[:3]
        version = struct.unpack("!B", chunk[3])[0]
        if header != "OST" or version != STREAMER_PROTOCOL_VERSION:
            # bad version
            print "Incompatible protocol version"
            return None
        filename_len = struct.unpack("!B", chunk[4])[0]
        filename = chunk[5:filename_len+5]
        data = chunk[filename_len + 5:]
        data_size = struct.calcsize("!HLL")
        chunk_size, num_chunks, pos = struct.unpack("!HLL", data[:data_size])
        payload = data[data_size:]
        return filename, chunk_size, num_chunks, pos, payload

    def put_chunk(self, chunk):
        """Puts a chunk back into file and refreshes the streamer constants"""
        res = self.decode_chunk(chunk)
        if not res:
            return
        filename, chunk_size, num_chunks, pos, payload = res
        new_pos = chunk_size * pos
        print new_pos
        self.fd.seek(new_pos, 0)
        self.fd.write(payload)

    def finish(self):
        """Finishes streaming"""
        self.fd.close()
        self.fd = None

if __name__ == "__main__":
    s = StreamerEncoder("streamer.py", 12)
    w = StreamerDecoder("output")
    s.prepare()
    num_chunks = s.get_num_chunks()
    chunks = s.get_chunks(range(num_chunks))
    keys = chunks.keys()
    keys.reverse()
    for c in keys:
        chunk = chunks[c]
        w.put_chunk(chunk)
    s.finish()
    w.finish()
