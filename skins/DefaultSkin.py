#!/usr/bin/python
"""
OpenClass default skin.

Copyright, (C) Eugeni Dodonov <eugeni@dodonov.net>, 2011

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
import pygtk
import gobject
from gtk import gdk

from skins import Skin

class DefaultSkin(Skin):
    def __init__(self, logger, gui):
        """Initializes default openclass skin"""
        Skin.__init__(self, logger, gui)

        # colors
        gui.color_normal = gtk.gdk.color_parse("#99BFEA")
        gui.color_active = gtk.gdk.color_parse("#FFBBFF")
        gui.color_background = gtk.gdk.color_parse("#FFFFFF")

        # building the interface
        gui.window = gtk.Window()
        gui.window.set_resizable(False)
        gui.window.set_default_size(800, 600)
        gui.window.set_position(gtk.WIN_POS_CENTER)
        gui.window.set_title(_("OpenClass Teacher"))
        gui.window.connect('destroy', gui.quit)

        # main layout
        MainLayout = gtk.Fixed()
        MainLayout.set_property("width_request", 640)
        MainLayout.set_property("height_request", 480)
        gui.window.add(MainLayout)

        MenuVBox = gtk.VBox()
        MenuVBox.set_property("width_request", 160)
        MenuVBox.set_property("height_request", 520)
        MainLayout.put(MenuVBox, 10, 20)
        gui.SendScreen = gtk.Button(_("Send Screen"))
        gui.SendScreen.connect('clicked', gui.send_screen)
        MenuVBox.pack_start(gui.SendScreen, False, False, 5)

        gui.LockScreen = gtk.Button(_("Lock Screens"))
        gui.LockScreen.connect('clicked', gui.lock_screen)
        MenuVBox.pack_start(gui.LockScreen, False, False, 5)

        gui.ShareFile = gtk.Button(_("Share files"))
        gui.ShareFile.connect('clicked', gui.share_files)
        MenuVBox.pack_start(gui.ShareFile, False, False, 5)

        gui.ShareFile = gtk.Button(_("Share a web page"))
        gui.ShareFile.connect('clicked', gui.share_url)
        MenuVBox.pack_start(gui.ShareFile, False, False, 5)

        gui.ShareFile = gtk.Button(_("Turn off students"))
        gui.ShareFile.connect('clicked', gui.shutdown)
        MenuVBox.pack_start(gui.ShareFile, False, False, 5)

        MenuVBox.pack_start(gtk.Label(), False, False, 100)

        gui.QuitButton = gtk.Button(_("Quit"))
        gui.QuitButton.connect('clicked', gui.quit)
        MenuVBox.pack_start(gui.QuitButton, False, False, 5)

        # scrolling machine view
        MachinesScrollWindow = gtk.ScrolledWindow()
        MachinesScrollWindow.set_property("width_request", 580)
        MachinesScrollWindow.set_property("height_request", 520)
        MainLayout.put(MachinesScrollWindow, 200, 30)

        gui.MachineLayout = gtk.Layout()
        MachinesScrollWindow.add(gui.MachineLayout)

        # machines images
        gui.image_connected = gui.get_img("iface/machine.png")
        gui.image_disconnected = gui.get_img("iface/machine_off.png")

        # screenshot view
        gui.shot_window = gtk.Window()
        gui.shot_window.set_title(_("Student view"))
        gui.shot_window.connect('destroy', lambda *w: gui.shot_window.hide())
        vbox = gtk.VBox()
        gui.shot_window.add(vbox)
        hbox = gtk.HBox()
        vbox.pack_start(hbox, False, False)
        gui.shot_label = gtk.Label()
        hbox.pack_start(gui.shot_label, False, False)

        gui.shot_share = gtk.Button(_("Share with other students"))
        gui.shot_share.connect('clicked', gui.share_student_screen)
        # mark currently refreshed client
        hbox.pack_start(gui.shot_share)

        gui.shot_refresh = gtk.Button(_("Refresh"))
        gui.shot_refresh.connect('clicked', gui.refresh_shot)
        # mark currently refreshed client
        gui.shot_refresh.current_client = None
        hbox.pack_start(gui.shot_refresh)

        button = gtk.Button(_("Close"))
        button.connect('clicked', lambda *w: gui.shot_window.hide())
        hbox.pack_start(button)

        gui.shot_drawing = gtk.Image()
        vbox.pack_start(gui.shot_drawing)

        vbox.show_all()

        # tooltips
        gui.tooltip = gtk.Tooltips()

        # Muda o background
        gui.window.modify_bg(gtk.STATE_NORMAL, gui.color_background)
        gui.MachineLayout.modify_bg(gtk.STATE_NORMAL, gui.color_background)

        # Mostra as maquinas
        gui.MachineLayout.show_all()

