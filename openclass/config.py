#!/usr/bin/python
"""OpenClass configuration module

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
import ConfigParser
from openclass import system

class Config:
    """Configuration parsing class"""
    def __init__(self, logger, configfile, master_configfile=None, defaults={}):
        """Initializes configuration"""
        self.logger = logger
        self.configfile = configfile
        self.master_configfile = master_configfile
        self.defaults = defaults

    def load(self):
        """Reads configuration"""
        self.config = ConfigParser.ConfigParser(self.defaults)
        try:
            if self.master_configfile:
                self.logger.info("Reading master configfile %s" % self.master_configfile)
                self.config.read(self.master_configfile)
            self.logger.info("Reading configfile %s" % self.configfile)
            self.config.read(self.configfile)
        except:
            self.logger.exception("Reading configfile")

    def save(self):
        """Writes configuration"""
        self.logger.info("Writing configfile %s" % self.configfile)
        try:
            with open(self.configfile, "w") as fd:
                self.config.write(fd)
        except:
            self.logger.exception("Writing configfile")

    def get(self, section, variable, default):
        """Gets a variable from a section of config"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        if not self.config.has_option(section, variable):
            self.config.set(section, variable, default)
        value = self.config.get(section, variable)
        return value
