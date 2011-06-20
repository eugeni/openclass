#!/usr/bin/python
"""
OpenClass teacher module.

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

import socket
import struct

import os
import gtk
import pygtk
import gobject
from gtk import gdk

from multiprocessing import Queue
import SocketServer
import socket
import urllib
from threading import Thread

import gettext
import __builtin__
__builtin__._ = gettext.gettext

try:
    gettext.install("openclass")
except IOError:
    _ = str
    traceback.print_exc()

# configuration
from openclass import network, system, protocol, screen, notification, config
import skins

# variables
MACHINES_X = 5
MACHINES_Y = 8

CONFIGFILE = system.get_full_path(system.get_local_storage(), ".openclass.conf")
SYSTEM_CONFIGFILE = system.get_full_path(system.get_system_storage(), "openclass.conf")

# {{{ TeacherRunner
class TeacherRunner(Thread):
    selected_machines = 0
    """Teacher service"""
    def __init__(self, logger, config):
        """Initializes the teacher thread"""
        Thread.__init__(self)

        # logger
        self.logger = logger

        # configuration
        self.config = config

        # actions
        self.actions = Queue()

        # connected machines
        self.clients = {}

        # actions for clients
        self.clients_actions = {}

        # authorized files for transfer
        self.authorized_files = []

        # protocol
        self.protocol = protocol.Protocol(self.logger)

        # listening server
        self.server = network.HTTPListener(self)

        # broadcast sender
        self.bcast = None

        # multicast sender
        try:
            self.mcast_frequency = float(self.config.get("multicast", "min_interval", "0.05"))
        except:
            self.logger.exception("Detecting multicast interval")
            self.mcast_frequency = 0.05
        self.mcast = network.McastSender(logger=logger, interval = self.mcast_frequency)

        # temporary files
        self.tmpfiles = []

    def add_temporary_file(self, suffix=''):
        """Creates a temporary file"""
        tmpfile = system.create_tmp_file(suffix=suffix)
        self.tmpfiles.append(tmpfile)
        return tmpfile

    def process_request(self, client, request, params):
        """Gets pending actions for a client"""
        self.logger.debug("Processing requests for %s (%s)" % (client, request))
        response = None
        response_params = None
        if request == protocol.REQUEST_REGISTER:
            # registering
            name = params.get("name", None)
            # decompress parameters in form of url request
            if name:
                name = name[0]
            else:
                name = client
            client_status = self.clients.get(client, "pending")
            if client_status == "pending":
                # register student by default, and allow teacher to disconnect it later
                self.add_client(client, name)
                self.clients[client] = "registered"
                response = "registered"
            elif client_status == "rejected":
                response = "rejected"
                self.reject_client(client, name)
            elif client_status == "registered":
                response = "registered"
            else:
                self.logger.error("Error: unknown status for %s: %s" % (client, self.clients[client]))
        elif request == protocol.REQUEST_ACTIONS:
            # student could send us additional params
            # if client is still unknown, default it to "pending" state
            client_status = self.clients.get(client, "pending")
            if client_status == "pending" or client_status == "rejected":
                # not registered yet, or not allowed in this class
                response = protocol.ACTION_PLEASEREGISTER
            elif client_status == "registered":
                # update client with new information (if any)
                name = params.get("name", None)
                if name:
                    name = name[0]
                shot = params.get("shot", None)
                self.add_client(client, name, shot)
                # checking actions for the client
                response = self.gui.current_action
                if client in self.clients_actions:
                    if len(self.clients_actions[client]) > 0:
                        response, response_params = self.clients_actions[client].pop(0)
            else:
                    self.logger.error("Error: unknown status for %s: %s" % (client, client_status))
                    # don't know what to do with this student, tell it to go away
                    response = protocol.ACTION_PLEASEREGISTER
        elif request == protocol.REQUEST_RAISEHAND:
            # student raised his hand
            self.logger.info("Student called your attention")
            question = params.get("message", None)
            if question:
                question = question[0]
                self.raise_hand(client, message=question)
            else:
                self.raise_hand(client)
        elif request == protocol.REQUEST_SHOWSCREEN:
            # student wants to show his screen
            self.logger.info("Student wants to show his screen to you")
            try:
                width = int(params["width"][0])
                height = int(params["height"][0])
                shot = params["shot"][0]
                self.gui.queue_show_screenshot(client, width, height, shot)
            except:
                self.logger.exception("Error parsing screenshot information")
        elif request == protocol.REQUEST_GETFILE:
            if 'file' not in params:
                response = _("Bad request for file")
            else:
                filename = urllib.unquote(params['file'][0])
                self.logger.info("Asked to open %s" % filename)
                if filename not in self.authorized_files:
                    self.logger.error("Error: %s not authorized for transfer to %s" % (filename, client))
                    response = _("File not authorized for transfer")
                else:
                    try:
                        with open(filename) as fd:
                            response = fd.read()
                            response_params = ""
                    except:
                        response = _("Unable to transfer %s: %s") % (filename, sys.exc_value)
        return response, response_params

    def quit(self):
        """Tells everything to quit"""
        self.actions.put(("quit", None))
        if self.bcast:
            self.bcast.actions.put(1)
        self.mcast.quit()
        self.server.actions.put(1)

        # remove temporary files
        for z in self.tmpfiles:
            try:
                os.unlink(z)
            except:
                self.logger.exception("Error removing temp files")

    def set_gui(self, gui):
        """Associates a GUI to this service"""
        self.gui = gui

    def add_client(self, client, name, shot=None):
        """Adds a new client"""
        self.gui.add_client(client, name, shot)

    def reject_client(self, client, name):
        """Rejects a client"""
        self.gui.reject_client(client, name)

    def raise_hand(self, client, message=_("The student asks for your attention")):
        """Calls teacher attention"""
        self.gui.queue_raise_hand(client, message)

    def disconnect_student(self, client, message=_("The teacher asked you to leave this class")):
        """Disconnects a student"""
        self.clients[client] = "rejected"

    def reconnect_student(self, client):
        """Allow the student to join the class again"""
        self.clients[client] = "pending"

    def add_client_action(self, client, action, params=None):
        """Adds an action for a client into a list"""
        if client not in self.clients_actions:
            self.clients_actions[client]=[]
        self.clients_actions[client].append((action, params))

    def authorize_file_transfer(self, filename):
        """Authorizes a local file for sharing with students"""
        self.authorized_files.append(filename)

    def start_multicast(self):
        """Starts multicast thread"""
        self.mcast.start()

    def start_broadcast(self, class_name):
        """Start broadcasting service"""
        self.bcast = network.BcastSender(self.logger, network.LISTENPORT, self.protocol.create_announce(class_name))
        self.class_name = class_name
        self.bcast.start()

    def send_projection(self, width, height, fullscreen, chunks):
        """Send chunks of projection over multicast"""
        for chunk in chunks:
            self.mcast.put(self.protocol.pack_chunk(width, height, fullscreen, chunk))

    def run(self):
        """Starts a background thread"""
        while 1:
            action = self.actions.get()
            if not action:
                continue
            # chegou ALGO
            name, parameters = action
            self.logger.info("Running %s" % name)
            if name == "quit":
                return
            else:
                self.logger.error("Unknown action %s" % name)
# }}}

# {{{ TeacherGui
class TeacherGui:
    selected_machines = 0
    """Teacher GUI main class"""
    def __init__(self, service, logger, config):
        """Initializes the interface"""
        # logger
        self.logger = logger
        self.config = config
        # internal variables
        self.class_name = None
        self.bcast = None
        self.clients_queue = Queue()
        self.service = service
        self.service.set_gui(self)

        # notification
        self.notification = notification.Notification("OpenClass teacher")

        # find out what is our skin
        skin_name = self.config.get("gui", "skin", "DefaultSkin")
        skin_class = skins.get_skin(logger, skin_name)
        self.skin = skin_class(logger, self)

        self.machines = {}
        self.machines_map = {}
        self.machines_status = {}

        # inicializa o timestamp
        self.curtimestamp = 0

        # projection screen
        self.projection_screen = screen.Screen()
        self.projection_width = None
        self.projection_height = None

        # Inicializa a matriz de maquinas
        self.machine_layout = [None] * MACHINES_X
        for x in range(0, MACHINES_X):
            self.machine_layout[x] = [None] * MACHINES_Y

        # maquinas de estados
        self.current_action = protocol.ACTION_NOOP

        # Configura os timers
        # monitora os eventos
        try:
            self.events_frequency = int(self.config.get("gui", "events_frequency", "1000"))
        except:
            self.logger.exception("Detecting events exception")
            self.events_frequency = 1000
        gobject.timeout_add(self.events_frequency, self.monitor)
        # monitora a projecao
        try:
            self.projection_frequency = int(self.config.get("projection", "frequency", "500"))
        except:
            self.logger.exception("Detecting projection exception")
            self.events_frequency = 500

        gobject.timeout_add(self.projection_frequency, self.projection)

        self.window.show_all()

        self.login()

    def queue_show_screenshot(self, client, width, height, shot):
        """Show a screenshot for a client"""
        self.clients_queue.put(("shot", client, {"width": width, "height": height, "shot": shot}))

    def login(self):
        """Asks teacher to login"""
        dialog = gtk.Dialog(_("Login"), self.window, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK)
                )
        dialogLabel = gtk.Label(_("Please login"))
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        hbox = gtk.HBox()
        login = gtk.Label(_("Your name (teacher or class name):"))
        hbox.pack_start(login)
        entry_login = gtk.Entry()
        entry_login.set_text(system.get_user_name())
        hbox.pack_start(entry_login)
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.vbox.pack_start(hbox)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.class_name = entry_login.get_text()
            self.logger.info("Login: %s" % self.class_name)
            dialog.destroy()
            # Starting broadcasting service
            self.service.start_broadcast(self.class_name)
            self.service.start_multicast()
            self.service.server.start()
            return True
        else:
            dialog.destroy()
            sys.exit(0)
            self.logger.info("leaving..")
            return None

    def ask_resolution(self, title=_("Please select screen size for projection")):
        """Determines resolution of screen projection"""
        # cria a janela do dialogo
        dialog = gtk.Dialog(title, self.window, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(title)
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        combobox = gtk.combo_box_new_text()
        combobox.append_text(_("Full screen size"))
        for res in screen.RESOLUTIONS:
            combobox.append_text(res)
        combobox.set_active(0)
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.vbox.add(combobox)
        dialog.show_all()
        response = dialog.run()
        # desired width and hight
        width = self.projection_screen.width
        height = self.projection_screen.height
        if response == gtk.RESPONSE_OK:
            exp = combobox.get_active_text()
            dialog.destroy()
            fullscreen = 0
            if exp != _("Full screen size"):
                try:
                    width, height = exp.split("x", 1)
                    width = int(width)
                    height = int(height)
                except:
                    self.logger.exception("Error discovering resolution")
            else:
                    fullscreen = 1
            self.projection_width = width
            self.projection_height = height
            self.projection_fullscreen = fullscreen
            return True
        else:
            dialog.destroy()
            return None

    def confirm(self, title, content):
        """Displays a confirmation dialog"""
        dialog = gtk.Dialog(title, self.window, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(content)
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_OK:
            return True
        else:
            return False


    def question(self, title, input=None):
        """Asks a question :)"""
        # cria a janela do dialogo
        dialog = gtk.Dialog(_("Question"), self.window, 0,
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

    def show_message(self, title, message, timeout=0):
        """Shows a message to student"""
        self.notification.notify(title, message, timeout)
        return

    def reject_client(self, client, name):
        """Rejects a client"""
        self.logger.info("Rejecting %s" % client)
        self.clients_queue.put(("reject", client, {"name": name}))

    def add_client(self, client, name, shot=None):
        """Adds a new client"""
        self.clients_queue.put(("new", client, {"name": name, "shot": shot}))

    def queue_raise_hand(self, client, message):
        """A student calls for attention"""
        self.logger.info("Student %s asks for attention: %s" % (client, message))
        self.clients_queue.put(("raisehand", client, {"message": message}))

    def put_machine(self, machine):
        """Puts a client machine in an empty spot"""
        for y in range(0, MACHINES_Y):
            for x in range(0, MACHINES_X):
                if not self.machine_layout[x][y]:
                    self.machine_layout[x][y] = machine
                    self.MachineLayout.put(machine, x * 70, y * 65)
                    machine.machine_x = x
                    machine.machine_y = y
                    return
        self.logger.error("Not enough layout space to add a machine!")

    def projection(self):
        """Grabs the screen for multicast projection when needed"""
        if self.current_action == protocol.ACTION_PROJECTION:
            self.logger.info("Sending screens, yee-ha!")
            # how many chunks?
            # TODO: auto-detect this according to the screen size
            try:
                chunks_x = int(self.config.get("projection", "tiles_x", "4"))
                chunks_y = int(self.config.get("projection", "tiles_y", "4"))
            except:
                self.logger.exception("Detecting number of chunks")
                chunks_x = 4
                chunks_y = 4
            # we are projecting, grab stuff

            chunks = self.projection_screen.chunks(chunks_x=chunks_x,
                    chunks_y=chunks_y, scale_x=self.projection_width,
                    scale_y=self.projection_height)

            self.service.send_projection(self.projection_width,
                    self.projection_height, self.projection_fullscreen, chunks)

        gobject.timeout_add(self.projection_frequency, self.projection)

    def refresh_shot(self, widget):
        """Refreshes a screenshot"""
        self.service.add_client_action(self.shot_refresh.current_client, protocol.ACTION_SHOT)

    def share_student_screen(self, widget):
        """Shares a student screen picture with other students"""
        # save current pixbuf and share it with everyone except currently
        # connected client
        tmpfile = self.service.add_temporary_file(suffix=".jpg")
        self.shot_drawing.get_pixbuf().save(tmpfile, "jpeg", {"quality": "75"})

        client = self.shot_refresh.current_client
        machines = [x for x in self.get_selected_machines() if x != client]
        self.service.authorize_file_transfer(tmpfile)
        for machine in machines:
            self.logger.info("Sharing with %s" % machine)
            self.service.add_client_action(machine, protocol.ACTION_OPENFILE, tmpfile)

    def show_screenshot(self, client, width, height, shot):
        """Displays a student screenshot"""
        self.shot_window.resize(width, height)
        self.shot_label.set_text(_("Viewing display of %s") % client)
        self.shot_refresh.current_client = client

        loader = gdk.PixbufLoader(image_type="jpeg")
        loader.write(shot)
        loader.close()
        pb = loader.get_pixbuf()

        self.shot_drawing.set_from_pixbuf(pb)

        self.shot_window.show()

    def monitor(self):
        """Monitors new machines connections"""
        while not self.clients_queue.empty():
            action, addr, params = self.clients_queue.get()
            if action == "new":
                # adding a new machine
                if addr not in self.machines:
                    # Maquina nova
                    gtk.gdk.threads_enter()
                    name = params.get("name", addr)

                    machine = self.mkmachine(name)
                    machine.fullname = name
                    machine.button.connect('button_press_event', self.cb_machine, machine)
                    self.put_machine(machine)
                    self.machines[addr] = machine
                    self.machines_map[machine] = addr
                    self.machines_status[addr] = "registered"
                    # show default image
                    machine.button.set_image(self.image_connected)
                    machine.show_all()
                    gtk.gdk.threads_leave()
                else:
                    # do not process events from already rejected machines
                    if self.machines_status[addr] == "rejected":
                        continue
                    machine = self.machines[addr]
                    shot = params.get("shot")
                    if shot:
                        loader = gdk.PixbufLoader(image_type="jpeg")
                        loader.write(shot[0])
                        loader.close()
                        pb = loader.get_pixbuf()
                        img = gtk.Image()
                        img.set_from_pixbuf(pb)
                        machine.button.set_image(img)
                    name = params.get("name")
                    if name:
                        machine.label.set_markup(self.mkname(name))
                        machine.fullname = name
                    tooltip = "%s\n" % name
                    tooltip += "(%s)\n" % addr
                    tooltip += _("Updated on %s") % time.asctime()
                    self.tooltip.set_tip(machine, tooltip)
            elif action == "reject":
                machine = self.machines[addr]
                machine.button.set_image(self.image_disconnected)
            elif action == "shot":
                # show a student screenshot
                width = params["width"]
                height = params["height"]
                shot = params["shot"]

                self.show_screenshot(addr, width, height, shot)
            elif action == "raisehand":
                message = params["message"]
                # shows a raisehand request from students
                name = addr
                if addr in self.machines:
                    name = self.machines[addr].machine
                self.show_message(_("Message received from %s") % name, message, timeout=0)

        gobject.timeout_add(self.events_frequency, self.monitor)

    def send_screen(self, widget):
        """Starts screen sharing for selected machines"""
        machines = self.get_selected_machines()
        self.logger.info("Sending screen to %s" % machines)
        if self.current_action != protocol.ACTION_PROJECTION:
            self.logger.info("Sending screens")
            res = self.ask_resolution()
            if not res:
                return
            self.SendScreen.set_label(_("Stop sending screen"))
            self.current_action = protocol.ACTION_PROJECTION
            self.LockScreen.set_sensitive(False)
            for machine in machines:
                self.service.add_client_action(machine, protocol.ACTION_PROJECTION)
        else:
            self.logger.info("Stopping sending screens")
            self.SendScreen.set_label(_("Send Screen"))
            self.current_action = protocol.ACTION_NOOP
            self.LockScreen.set_sensitive(True)
            for machine in machines:
                self.service.add_client_action(machine, protocol.ACTION_NOOP)

    def share_url(self, widget, client=None):
        """Shares an URL with students"""
        url = self.question(_("Share a web page with students"), "http://")
        if not url:
            return
        if not client:
            machines = self.get_selected_machines()
        else:
            machines = [client]
        for machine in machines:
            self.service.add_client_action(machine, protocol.ACTION_OPENURL, url)

    def disconnect(self, widget, client=None):
        """Disconnect a student from teacher"""
        if not client:
            # TODO: it is too dangerous to disconnect everyone, no?
            machines = self.get_selected_machines()
        else:
            machines = [client]
        for machine in machines:
            disconnect_message=_("The teacher asked you to leave this class")
            self.service.disconnect_student(machine, message=disconnect_message)
            # now back to the machine image
            machine_img = self.machines.get(machine, None)
            if not machine_img:
                self.logger.error("Error: unable to locate pixmap for machine %s" % client)
                return
            machine_img.button.set_image(self.image_disconnected)
            self.machines_status[machine] = "rejected"
            self.tooltip.set_tip(machine_img, _("Disconnected from teacher at %s!") % (time.asctime()))

    def reconnect(self, widget, client=None):
        """Reconnect a student to the teacher"""
        if not client:
            # TODO: it is too dangerous to disconnect everyone, no?
            machines = self.get_selected_machines()
        else:
            machines = [client]
        for machine in machines:
            self.service.reconnect_student(machine)
            # now back to the machine image
            machine_img = self.machines.get(machine, None)
            if not machine_img:
                self.logger.error("Error: unable to locate pixmap for machine %s" % client)
                return
            self.machines_status[machine] = "registered"
            machine_img.button.set_image(self.image_connected)

    def shutdown(self, widget, client=None):
        """Shares an URL with students"""
        if not client:
            confirm = self.confirm(_("Please confirm the shutdown request"), _("Are you sure you want to turn off all the student computers?"))
        else:
            confirm = self.confirm(_("Please confirm the shutdown request"), _("Are you sure you want to turn off this computer?"))
        if not confirm:
            return
        if not client:
            machines = self.get_selected_machines()
        else:
            machines = [client]
        for machine in machines:
            self.service.add_client_action(machine, protocol.ACTION_SHUTDOWN)

    def share_files(self, widget, client=None):
        """Shares a file with students"""
        chooser = gtk.FileChooserDialog(title=_("Select a file to share with students"),action=gtk.FILE_CHOOSER_ACTION_OPEN,
                      buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        checkbox = gtk.CheckButton(label=_("Open the file on students immediately"))
        checkbox.set_active(True)
        chooser.vbox.pack_start(checkbox, False, False)
        chooser.vbox.show_all()
        response = chooser.run()
        if response != gtk.RESPONSE_OK:
            chooser.destroy()
            return
        filename = chooser.get_filename()
        do_open = checkbox.get_active()
        # discover short filename
        filename_short = filename.split(os.sep)[-1]
        self.service.authorize_file_transfer(filename)
        chooser.destroy()
        if do_open:
            file_action="open::%s" % filename
        else:
            file_action="down:%s:%s" % (filename_short, filename)
        if not client:
            machines = self.get_selected_machines()
        else:
            machines = [client]
        for machine in machines:
            self.service.add_client_action(machine, protocol.ACTION_OPENFILE, file_action)

    def lock_screen(self, widget):
        """Starts screen locking for selected machines"""
        machines = self.get_selected_machines()
        self.logger.info("Locking screen on %s" % machines)
        if self.current_action != protocol.ACTION_ATTENTION:
            self.logger.info("Locking screens")
            self.LockScreen.set_label(_("Stop locking screen"))
            self.current_action = protocol.ACTION_ATTENTION
            self.SendScreen.set_sensitive(False)
            for machine in machines:
                self.service.add_client_action(machine, protocol.ACTION_ATTENTION)
        else:
            self.logger.info("Stopping locking screens")
            self.LockScreen.set_label(_("Lock Screen"))
            self.current_action = protocol.ACTION_NOOP
            self.SendScreen.set_sensitive(True)
            for machine in machines:
                self.service.add_client_action(machine, protocol.ACTION_NOOP)

    def get_selected_machines(self):
        """Returns the list of all selected machines"""
        machines = []
        for z in self.machines:
            machine = self.machines[z]
            # TODO: when machines will be removed from the class, remove them
            # from this array as well. For now, we add everything
            machines.append(z)
        return machines

    def quit(self, widget):
        """Main window was closed"""
        self.logger.info("Closing pending threads..")
        self.service.quit()
        gtk.main_quit()
        self.logger.info("done")

    def get_img(self, imgpath):
        """Returns image widget if exists"""
        img = gtk.Image()
        try:
            img.set_from_file(imgpath)
        except:
            self.logger.exception("Getting image from %s" % imgpath)
        return img

    def mkmachine(self, name):
        """Creates a client representation"""
        box = gtk.VBox(homogeneous=False)

        img = gtk.Image()
        img.set_size_request(64, 64)

        button = gtk.Button()
        button.set_image(img)
        box.pack_start(button, expand=False)

        label = gtk.Label(_("name"))
        label.set_use_markup(True)
        label.set_markup(self.mkname(name))
        box.pack_start(label, expand=False)

        self.tooltip.set_tip(box, name)

        # Sets private variables
        box.machine = name
        box.button = button
        box.label = label
        return box

    def mkname(self, name):
        """Creates a pretty-printed name"""
        if len(name) > 0:
            name = "%s.." % name[:8]
        return "<small>%s</small>" % name

    def send_msg_student(self, widget, machine):
        """Send a message to student"""
        message = self.question(_("Send a message to student"), _("Please, pay attention!"))
        if not message:
            return
        self.logger.info("Will send: %s" % message)
        self.service.add_client_action(machine, protocol.ACTION_MSG, message)

    def request_screenshot(self, widget, machine):
        """Request screenshot from student"""
        self.service.add_client_action(machine, protocol.ACTION_SHOT)
        self.logger.info("Sending request to %s" % machine)

    def cb_machine(self, widget, event, machine):
        """Callback when clicked on a client machine"""

        if machine in self.machines_map:
            machine = self.machines_map[machine]
        else:
            # unknown machine?
            self.logger.error("Error: unknown machine %s!" % machine)
            return

        # is machine rejected?
        status = self.machines_status.get(machine, "registered")

        # popup menu
        popup_menu = gtk.Menu()

        if status == "registered":
            menu_msg = gtk.MenuItem(_("Send message to student"))
            menu_msg.connect("activate", self.send_msg_student, machine)
            popup_menu.append(menu_msg)

            menu_view = gtk.MenuItem(_("View student screen"))
            menu_view.connect("activate", self.request_screenshot, machine)
            popup_menu.append(menu_view)

            menu_url = gtk.MenuItem(_("Send a web page to student"))
            menu_url.connect("activate", self.share_url, machine)
            popup_menu.append(menu_url)

            menu_file = gtk.MenuItem(_("Send a file to student"))
            menu_file.connect("activate", self.share_files, machine)
            popup_menu.append(menu_file)

            menu_control = gtk.MenuItem(_("Remote control student computer"))
            menu_control.set_sensitive(False)
            popup_menu.append(menu_control)

            menu_disconnect = gtk.MenuItem(_("Remove student from class"))
            menu_disconnect.connect("activate", self.disconnect, machine)
            popup_menu.append(menu_disconnect)

            menu_shutdown = gtk.MenuItem(_("Turn off student computer"))
            menu_shutdown.connect("activate", self.shutdown, machine)
            popup_menu.append(menu_shutdown)

        elif status == "rejected":
            menu_msg = gtk.MenuItem(_("Allow student to participate in the class"))
            menu_msg.connect("activate", self.reconnect, machine)
            popup_menu.append(menu_msg)
        elif status == "pending":
            # for teacher-side machine authorization, please see service
            # thread to see how it should work, namely the REGISTER message
            # for now, do nothing
            return
        else:
            self.logger.error("Unknown machine status for %s: %s" % (machine, status))
            return

        popup_menu.show_all()
        popup_menu.popup(None, None, None, event.button, event.time)
        return
# }}}

if __name__ == "__main__":
    # configure logging
    logger = system.setup_logger("openclass_teacher")

    # configuration file
    config = config.Config(logger, CONFIGFILE, SYSTEM_CONFIGFILE)
    config.load()

    # configura o timeout padrao para sockets
    socket.setdefaulttimeout(2)
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    logger.info("Starting broadcast..")
    # Main service service
    service = TeacherRunner(logger, config)
    # Main interface
    gui = TeacherGui(service, logger, config)
    service.start()

    logger.info("Starting main loop..")
    gtk.main()
    # saving config changes and reference values
    config.save()
    gtk.gdk.threads_leave()
