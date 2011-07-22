#!/usr/bin/python
"""
OpenClass student module.

Copyright, (C) Eugeni Dodonov <eugeni@dodonov.net>, 2008-2011

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
import traceback
import time

from multiprocessing import Queue

import socket
import SocketServer
import struct

import os
import logging
import gtk
import pygtk
import gobject
from gtk import gdk

from threading import Thread
import thread
import socket
import traceback
import time

import urllib, urllib2
import math

import gettext
import __builtin__
__builtin__._ = gettext.gettext

try:
    gettext.install("openclass")
except IOError:
    _ = str
    traceback.print_exc()

from openclass import network, system, protocol, screen, notification, config
import skins

# variables
CONFIGFILE = system.get_full_path(system.get_local_storage(), ".openclass-student.conf")
SYSTEM_CONFIGFILE = system.get_full_path(system.get_system_storage(), "openclass-student.conf")
class Student:
    selected_machines = 0
    """Teacher GUI main class"""
    def __init__(self, logger, config):
        """Initializes the interface"""
        # logger
        self.logger = logger
        # config
        self.config = config
        # colors
        self.color_normal = gtk.gdk.color_parse("#99BFEA")
        self.color_active = gtk.gdk.color_parse("#FFBBFF")
        self.color_background = gtk.gdk.color_parse("#FFFFFF")

        # notification
        self.notification = notification.Notification("OpenClass student")

        # screen
        self.screen = screen.Screen()

        # find out what is our skin
        skin_name = self.config.get("student", "skin", "DefaultSkinStudent")
        skin_class = skins.get_skin(logger, skin_name)
        self.skin = skin_class(logger, self)

        # discover unique client ID (if any)
        # specially useful for multi-seat configurations
        self.client_id = system.get_client_id()

        # protocol handler
        self.protocol = protocol.Protocol(self.logger)

        # Configura o timer
        gobject.timeout_add(1000, self.monitor_bcast)
        gobject.timeout_add(500, self.monitor_mcast)
        gobject.timeout_add(1000, self.monitor_teacher)

        self.teacher = None
        self.teacher_addr = None
        self.name = None
        self.outfile = None
        self.missed_commands = 0
        try:
            self.max_missed_commands = int(self.config.get("student", "max_missed_commands", "30"))
        except:
            self.logget.exception("Detecting max missed commands")
            self.max_client_timeout = 30

        # Inicializa as threads
        self.bcast = network.BcastListener(logger=self.logger, port=network.LISTENPORT)
        self.logger.info("Starting broadcasting service..")
        self.bcast.start()

        self.mcast = network.McastListener()

        # initialize list of teachers
        self.teachers = gtk.combo_box_new_text()
        self.teachers_addr = {}

        # disconnected by default
        self.disconnect()

        # Building UI
        self.__grabwindow = None

        # login dialog
        self.create_login_dialog(None)
        self.login(None)

    def disconnect(self):
        """Disconnected from teacher"""
        self.icon.set_from_file("iface/machine_off.png")
        self.icon.set_tooltip(_('OpenClass student (disconnected)'))
        teacher_label = self.manager.get_widget('/Menubar/Menu/Teacher')
        teacher_label.get_children()[0].set_markup(_("Disconnected from teacher"))
        teacher_label.get_children()[0].set_use_markup(True)
        self.teacher = None
        self.teacher_addr = None
        # enable quit button
        quit = self.manager.get_widget('/Menubar/Menu/Quit')
        quit.set_sensitive(True)

    def connect_to_teacher(self, teacher):
        """Connect to teacher"""
        self.icon.set_from_file("iface/machine.png")
        self.icon.set_tooltip(_('OpenClass student (connected to %s)') % self.teacher)
        teacher_label = self.manager.get_widget('/Menubar/Menu/Teacher')
        teacher_label.get_children()[0].set_markup(_("Connected to <b>%s</b>") % self.teacher)
        teacher_label.get_children()[0].set_use_markup(True)
        # disable quit button
        quit = self.manager.get_widget('/Menubar/Menu/Quit')
        quit.set_sensitive(False)

    def on_activate(self, data):
        """Tray icon is clicked"""
        pass

    def on_popup_menu(self, status, button, time):
        """Right mouse button is clicked on tray icon"""
        self.menu.popup(None, None, None, button, time)

    def choose_teacher(self, data):
        """Select different teacher or disconnection from current one"""
        return self.login(data)

    def question(self, title, input=None):
        """Asks a question :)"""
        # cria a janela do dialogo
        dialog = gtk.Dialog(_("Question"), None, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(title)
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        dialog.set_default_response(gtk.RESPONSE_OK)
        if input:
            entry = gtk.Entry()
            entry.set_text(input)
            dialog.vbox.add(entry)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            res = entry.get_text()
            dialog.destroy()
            if res:
                return res
            else:
                return True
        else:
            dialog.destroy()
            return None
    
    def block_keyboard_mouse(self):
        if not self.__grabwindow:
            self.__grabwindow = gtk.Invisible()
            self.__grabwindow.show()
            self.__grabwindow.realize()
        self.__block_mouse()
        gobject.idle_add(gtk.gdk.keyboard_grab,self.__grabwindow.window,True)
        
    def unblock_keyboard_mouse(self):
        gobject.idle_add(gtk.gdk.pointer_ungrab)
        gobject.idle_add(gtk.gdk.keyboard_ungrab)
     
    def __block_mouse(self):
        pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
        color = gtk.gdk.Color()
        invisible_cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)
        def grab_mouse():
            gtk.gdk.pointer_grab(self.__grabwindow.window,owner_events=True,cursor=invisible_cursor)
        gobject.idle_add(grab_mouse)
    
    def raise_hand(self, data):
        """Raise your hand to teacher"""
        question = self.question(_("Call teacher attention"), _("Teacher, look at me!"))
        if not question:
            return
        command, params = self.send_command(protocol.REQUEST_RAISEHAND, {"message": question})

    def on_about(self, data):
        dialog = gtk.AboutDialog()
        dialog.set_name('OpenClass')
        dialog.set_comments('An open-source small class control application.')
        dialog.set_website('http://openclass.dodonov.net/')
        dialog.run()
        dialog.destroy()

    def quit(self, widget, param):
        """Main window was closed"""
        gtk.main_quit()
        self.bcast.actions.put(1)
        self.mcast.actions.put(1)
        sys.exit(0)

    def leave_class(self, widget):
        """Leave a class"""
        pass

    def ask_attention(self, message=_("Teacher asked you for attention")):
        """Asks for attention"""
        self.attention_label.set_markup("<big><b>%s</b></big>" % message)
        self.attention_window.set_size_request(self.screen.width, self.screen.height)
        self.attention_window.show_all()
        self.attention_window.stick()
        self.block_keyboard_mouse()
        self.attention_window.fullscreen()

    def start_projection(self):
        """Starts screen projection"""
        self.projection_window.visible = True
        self.projection_window.stick()
        self.projection_window.show_all()

    def noop(self):
        """Back to noop state"""
        self.projection_window.visible = False
        self.projection_window.hide()
        self.attention_window.visible = False
        self.attention_window.hide()
        self.unblock_keyboard_mouse()

    def create_login_dialog(self, widget):
        """Asks student to login"""
        dialog = gtk.Dialog(_("Login"), None, gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(_("Please login"))
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        hbox = gtk.HBox()
        login = gtk.Label(_("Your name:"))
        hbox.pack_start(login)
        self.entry_login = gtk.Entry()
        self.entry_login.set_text(system.get_user_name())
        hbox.pack_start(self.entry_login)
        dialog.vbox.pack_start(hbox)
        # list of teachers
        hbox = gtk.HBox()
        teacher = gtk.Label(_("Your teacher:"))
        hbox.pack_start(teacher)
        # list of teachers
        hbox.pack_start(self.teachers)
        dialog.vbox.pack_start(hbox)
        dialog.show_all()
        self.login_dialog = dialog

    def login(self, widget):
        """Shows the login dialog"""
        dialog = self.login_dialog
        while True:
            response = dialog.run()
            if response == gtk.RESPONSE_OK:
                self.name = self.entry_login.get_text()
                self.logger.info("Login: %s" % self.name)
                teacher = self.teachers.get_active_text()
                if teacher in self.teachers_addr:
                    source = self.teachers_addr[teacher]
                else:
                    # unknown teacher?
                    self.logger.info("Unknown teacher address for teacher %s" % teacher)
                    continue
                self.logger.info("Will register on %s" % source)
                ret, params = self.send_command(protocol.REQUEST_REGISTER, {"name": self.name}, teacher=source)
                if ret == "registered":
                    # registered successfully
                    self.teacher = teacher
                    self.teacher_addr = source
                    self.connect_to_teacher(self.teacher)
                    # start threads
                    if not self.mcast.isAlive():
                        self.mcast.start()
                    dialog.hide()
                    name_label = self.manager.get_widget('/Menubar/Menu/Login')
                    name_label.get_children()[0].set_markup(_("Logged in as <b>%s</b>") % self.name)
                    name_label.get_children()[0].set_use_markup(True)
                    break
                elif ret == "pending":
                    self.logger.info("pending authorization from teacher")
                elif ret == "rejected":
                    self.logger.info("rejected by teacher")
                    self.notification.notify(_("Connection not allowed"), _("The teacher (%s) does not allows you to connect to his class") % teacher, 10)
                else:
                    self.logger.error("Unknown answer: %s" % ret)
            else:
                break
        dialog.hide()

    def monitor_teacher(self):
        """Periodically checks for teacher commands"""
        if self.teacher_addr:
            # send some parameters with the request
            params = {}
            params["name"] = self.name
            width, height, shot = self.screen.capture(scale_x=64, scale_y=64, quality=25)
            params["shot"] = shot
            # connect to teacher for instructions
            command, params = self.send_command(protocol.REQUEST_ACTIONS, params)
            if command == protocol.ACTION_PROJECTION:
                self.logger.info("Projecting")
                self.start_projection()
            elif command == protocol.ACTION_ATTENTION:
                self.logger.info( "Attention!")
                self.ask_attention()
            elif command == protocol.ACTION_MSG:
                self.logger.info("Message: %s" % params)
                self.show_message(params)
                self.noop()
            elif command == protocol.ACTION_NOOP:
                self.logger.info("Stopping everything")
                self.noop()
            elif command == protocol.ACTION_PLEASEREGISTER:
                self.logger.info("Students needs to register again")
                self.noop()
                self.disconnect()
            elif command == protocol.ACTION_SHOT:
                self.logger.info("Teacher requested our screenshot")
                self.shot()
            elif command == protocol.ACTION_OPENFILE:
                file_action = params
                self.logger.info("Teacher requested us to process file action: %s" % file_action)
                try:
                    do_open, filename_short, filename = file_action.split(":", 2)
                    filename = urllib.quote(filename)
                    url = "http://%s:%d/%s?file=%s" % (self.teacher_addr, network.LISTENPORT, protocol.REQUEST_GETFILE, filename)
                    self.logger.debug("Grabbing file from %s" % url)
                    if do_open == "open":
                        system.open_url(url)
                    else:
                        # just download the file, do not open it yet
                        try:
                            localfile = system.create_local_file(_("Received files"), filename_short)
                            opener = urllib.FancyURLopener().open(url)
                            with open(localfile, "w") as fd:
                                while True:
                                    data = opener.read(16384)
                                    if not data:
                                        break
                                    fd.write(data)
                            self.notification.notify(_("File download"), _("Received a file from teacher: %s") % localfile)
                        except:
                            self.logger.exception("Downloading file %s from teacher" % url)
                            self.notification.notify(_("File download"), _("Unable to download file %s from teacher.") % filename_short)
                except:
                    self.logger.exception("Open file request")
            elif command == protocol.ACTION_OPENURL:
                url = params
                self.logger.info("Teacher requested us to open the link at %s" % url)
                system.open_url(url)
            elif command == protocol.ACTION_SHUTDOWN:
                # TODO: show a confirmation window with a timeout
                system.shutdown()
            else:
                self.logger.error("Unknown command %s" % command)
        gobject.timeout_add(1000, self.monitor_teacher)

    def show_message(self, message):
        """Shows a message to student"""
        self.notification.notify(_("Message received from teacher"), message)
        return

    def shot(self):
        """Send a screenshot to teacher"""
        width, height, shot = self.screen.capture()
        params = {"width": width,
                "height": height,
                "shot": shot,
                "client_id": self.client_id
                }
        self.send_command(protocol.REQUEST_SHOWSCREEN, params=params, post=True)

    def send_command(self, command, params={}, teacher=None, post=False):
        """Sends a command to teacher via GET request (default) or POST (post=True)"""
        if not teacher:
            teacher = self.teacher_addr
        if not teacher:
            self.logger.error("Error: no teacher yet!")
            return None, None
        if not self.name:
            self.logger.error("Error: not logged in yet!")
            return None, None
        # TODO: proper user-agent
        url = "http://%s:%d/%s" % (teacher, network.LISTENPORT, command)
        params["client_id"] = self.client_id
        if post:
            params = urllib.urlencode(params)
        else:
            url += "?%s" % urllib.urlencode(params)
            params = None
        headers = {'User-Agent': 'openclass'}

        command = None
        params_ret = None
        try:
            req = urllib2.Request(url, params, headers)
            print req
            response = urllib2.urlopen(req)
            ret = response.read()
            try:
                if ret:
                    command, params_ret = ret.split(" ", 1)
            except:
                self.logger.exception("Parsing command from teacher")
                command = ret
                params_ret = None
            self.missed_commands = 0
        except:
            # something went wrong, disconnect
            self.missed_commands += 1
            if self.missed_commands > self.max_missed_commands:
                self.logger.warning("Too many missing commands, leaving this teacher")
                self.noop()
                self.teacher = None
                self.teacher_addr = None
                self.disconnect()
                self.logger.error("Unable to talk to teacher: %s" % sys.exc_value)
            self.logger.warning("Unable to talk to teacher for %d time: %s" % (self.missed_commands, sys.exc_value))
        return command, params_ret

    def monitor_mcast(self):
        """Monitor for multicast messages"""
        while not self.mcast.messages.empty():
            message, sender = self.mcast.messages.get()
            screen_width, screen_height, fullscreen, pos_x, pos_y, step_x, step_y, img = self.protocol.unpack_chunk(message)
            self.logger.debug("Received image at %dx%d-%dx%d (fullscreen=%s)" % (pos_x, pos_y, step_x, step_y, fullscreen))
            # ignore messages received from different teacher
            if sender != self.teacher_addr:
                self.logger.info( "Ignoring multicast request from other teacher (%s instead of %s)" % (sender, self.teacher_addr))
                continue
            try:
                loader = gdk.PixbufLoader(image_type="jpeg")
                loader.write(img)
                loader.close()
                pb = loader.get_pixbuf()

                gc = self.drawing.get_style().fg_gc[gtk.STATE_NORMAL]
                # are we in fullscreen mode ?
                if fullscreen == 1:
                    width = self.screen.width
                    height = self.screen.height
                    if width != screen_width or height != screen_height:
                        self.projection_window.set_size_request(screen_width, screen_height)
                        self.drawing.set_size_request(screen_width, screen_height)
                    if self.projection_window.is_fullscreen == False:
                        self.projection_window.set_has_frame(False)
                        self.projection_window.set_decorated(False)
                        self.block_keyboard_mouse()
                        self.projection_window.fullscreen()
                        self.projection_window.is_fullscreen = True
                    scaling_ratio_x = 1.0 * width / screen_width
                    scaling_ratio_y = 1.0 * height / screen_height
                else:
                    width, height = self.projection_window.get_size()
                    if width != screen_width or height != screen_height:
                        self.projection_window.set_size_request(screen_width, screen_height)
                        self.drawing.set_size_request(screen_width, screen_height)
                    if self.projection_window.is_fullscreen:
                        self.projection_window.set_has_frame(True)
                        self.projection_window.set_decorated(True)
                        self.projection_window.unfullscreen()
                        self.projection_window.is_fullscreen = False
                    scaling_ratio_x = 1
                    scaling_ratio_y = 1
                # drawing or scaling
                if scaling_ratio_x != 1 or scaling_ratio_y != 1:
                    # scaling received stuff
                    new_pos_x = math.ceil(pos_x * scaling_ratio_x)
                    new_pos_y = math.ceil(pos_y * scaling_ratio_y)
                    new_step_x = math.ceil(step_x * scaling_ratio_x)
                    new_step_y = math.ceil(step_y * scaling_ratio_y)
                    pb2 = pb.scale_simple(new_step_x, new_step_y, gtk.gdk.INTERP_BILINEAR)
                    self.drawing.window.draw_pixbuf(gc, pb2, 0, 0, new_pos_x, new_pos_y, new_step_x, new_step_y)
                else:
                    self.drawing.window.draw_pixbuf(gc, pb, 0, 0, pos_x, pos_y, step_x, step_y)

            except:
                self.logger.exception("Processing multicast message")

        gobject.timeout_add(1000, self.monitor_mcast)

    def monitor_bcast(self):
        """Monitors broadcast teacher status"""
        if self.bcast.has_msgs():
            data, source = self.bcast.get_msg()
            # if there is an announce, but we are not yet logged in, skip
            msg = self.protocol.parse_header(data)
            name, flags = self.protocol.parse_announce(msg)
            self.logger.debug("Found teacher <%s> at %s" % (name, source))
            model = self.teachers.get_model()
            if name not in [x[0] for x in model]:
                self.teachers.append_text(name)
                self.teachers_addr[name] = source
                # should we enable the login dialog?
                if len(model) > 0:
                    self.teachers.set_active(0)
            else:
                # same teacher
                pass
        gobject.timeout_add(1000, self.monitor_bcast)

if __name__ == "__main__":
    # configure logging
    logger = system.setup_logger("openclass_student")

    # configuration file
    config = config.Config(logger, CONFIGFILE, SYSTEM_CONFIGFILE)
    config.load()

    # configura o timeout padrao para sockets
    socket.setdefaulttimeout(5)
    # Atualizando a lista de interfaces
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()

    logger.info("Starting GUI..")
    gui = Student(logger=logger, config=config)
    gtk.main()
    config.save()
    gtk.gdk.threads_leave()
