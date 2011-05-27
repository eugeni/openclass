#!/usr/bin/python
"""OpenClass notification module.

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

import gtk
import gobject

try:
    import pynotify2
    _HAS_PYNOTIFY=True
except:
    _HAS_PYNOTIFY=False

class Notification:
    """A class which uses either pynotify, or, when it is not available,
    plain GTK windows to show something"""
    def __init__(self, title):
        """Initializes class"""
        if _HAS_PYNOTIFY:
            pynotify.init(title)
            self.pynotify = True
        else:
            # no pynotify
            self.title = title
            self.pynotify = False

    def notify(self, title, message, timeout=0):
        """Shows a notification for user"""
        if self.pynotify:
            n = pynotify.Notification(title, message)
            if timeout:
                n.set_timeout(timeout)
            n.show()
        else:
            window = gtk.Window()
            window.set_title(title)
            window.set_resizable(False)
            eventbox = gtk.EventBox()
            eventbox.set_events(gtk.gdk.BUTTON_PRESS_MASK)
            window.add(eventbox)
            # TODO: catch clicks
            eventbox.connect('button-press-event', self.clicked, window)
            vbox = gtk.VBox()
            eventbox.add(vbox)
            label = gtk.Label()
            label.set_markup("<b>%s</b>" % title)
            label.set_use_markup(True)
            vbox.pack_start(label)
            label = gtk.Label()
            label.set_markup("<i>%s</i>" % message)
            label.set_use_markup(True)
            vbox.pack_start(label)

            if timeout:
                gobject.timeout_add(timeout * 1000, self.clicked, None, None, window)

            window.show_all()

            # calculating screen size
            window.set_gravity(gtk.gdk.GRAVITY_SOUTH_EAST)
            width, height = window.get_size()
            window.move(gtk.gdk.screen_width() - width, gtk.gdk.screen_height() - height)

    def clicked(self, widget, event, window):
        """A window was clicked"""
        window.destroy()
