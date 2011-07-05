#!/usr/bin/python
"""
OpenClass default student skin.

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

class DefaultSkinStudent(Skin):
    def __init__(self, logger, gui):
        """Initializes default openclass skin"""
        Skin.__init__(self, logger, gui)
        # Building student UI
        gui.icon = gtk.StatusIcon()

        menu = '''
            <ui>
             <menubar name="Menubar">
              <menu action="Menu">
               <menuitem action="Login"/>
               <menuitem action="Teacher"/>
               <separator/>
               <menuitem action="RaiseHand"/>
               <separator/>
               <menuitem action="About"/>
               <separator/>
               <menuitem action="Quit"/>
              </menu>
             </menubar>
            </ui>
        '''
        actions = [
            ('Menu',  None, 'Menu'),
            ('Login', None, _('_Login'), None, _('Identify yourgui to the teacher'), gui.login),
            ('Teacher', gtk.STOCK_PREFERENCES, _('_Teacher'), None, _('Select your teacher'), gui.choose_teacher),
            ('RaiseHand', gtk.STOCK_INFO, _('_Call attention'), None, _('Raise your hand to call teacher attention'), gui.raise_hand),
            ('About', gtk.STOCK_ABOUT, _('_About'), None, _('About OpenClass'), gui.on_about),
            ('Quit', gtk.STOCK_QUIT, _('_Quit'), None, _('Quit class'), lambda *w: gui.quit(None, None))
            ]
        ag = gtk.ActionGroup('Actions')
        ag.add_actions(actions)
        gui.manager = gtk.UIManager()
        gui.manager.insert_action_group(ag, 0)
        gui.manager.add_ui_from_string(menu)
        gui.menu = gui.manager.get_widget('/Menubar/Menu/About').props.parent
        search = gui.manager.get_widget('/Menubar/Menu/Login')
        search.get_children()[0].set_markup('<b>_Login...</b>')
        search.get_children()[0].set_use_underline(True)
        search.get_children()[0].set_use_markup(True)

        gui.icon.set_visible(True)
        gui.icon.connect('activate', gui.on_activate)
        gui.icon.connect('popup-menu', gui.on_popup_menu)

        # drawing
        gui.projection_window = gtk.Window()
        gui.projection_window.set_resizable(False)
        #gui.projection_window.set_has_frame(False)
        #gui.projection_window.set_decorated(False)
        gui.projection_window.set_keep_above(True)
        gui.projection_window.connect('delete-event', lambda *w: True)
        gui.projection_window.visible = False
        gui.projection_window.is_fullscreen = False
        vbox = gtk.VBox()
        gui.projection_window.add(vbox)
        gui.gc = None
        gui.drawing = gtk.DrawingArea()
        gui.drawing.set_size_request(gui.screen.width, gui.screen.height)
        vbox.pack_start(gui.drawing)
        gui.projection_window.hide()

        # attention
        gui.attention_window = gtk.Window()
        gui.attention_window.set_resizable(False)
        gui.attention_window.set_has_frame(False)
        gui.attention_window.set_decorated(False)
        gui.attention_window.set_keep_above(True)
        gui.attention_window.connect('delete-event', lambda *w: True)
        gui.attention_window.visible = False

        vbox = gtk.VBox()
        gui.attention_window.add(vbox)
        gui.attention_label = gtk.Label()
        gui.attention_label.set_use_markup(True)
        vbox.pack_start(gui.attention_label)

        gui.attention_window.hide()

