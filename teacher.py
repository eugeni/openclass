#!/usr/bin/python
"""
Teacher GUI using GLADE
"""

# TODO: detectar quando conexoes nao sao estabelecidas
# TODO: tirar redundancias entre multicast e broadcast

import sys
import traceback
import time

import socket
import struct

import os
import logging
import gtk
import gtk.glade
import pygtk
import gobject

import Queue
import SocketServer
import socket
from threading import Thread

import gettext
import __builtin__
__builtin__._ = gettext.gettext

MACHINES_X = 8
MACHINES_Y = 8

# configuration
from openclass import network, system, protocol

# helper functions

# {{{ TeacherRunner
class TeacherRunner(Thread):
    selected_machines = 0
    """Teacher service"""
    def __init__(self):
        """Initializes the teacher thread"""
        Thread.__init__(self)

        # connected machines
        self.machines = []

        # actions
        self.actions = Queue.Queue()

        # protocol
        self.protocol = protocol.Protocol()

        # new clients
        self.new_clients_queue = Queue.Queue()

        # listening server
        self.server = network.HTTPListener(self)

        # broadcast sender
        self.bcast = None

    def process_request(self, client, request, seqno):
        """Gets pending actions for a client, starting with seqno"""
        print "Processing requests for %s (%s)" % (client, request)

    def quit(self):
        """Tells everything to quit"""
        self.actions.put(("quit", None))
        if self.bcast:
            self.bcast.actions.put(1)
        self.server.actions.put(1)

    def set_gui(self, gui):
        """Associates a GUI to this service"""
        self.gui = gui

    def add_client(self, client):
        """Adds a new client"""
        self.gui.add_client(client)

    def start_broadcast(self, class_name):
        """Start broadcasting service"""
        self.bcast = network.BcastSender(network.LISTENPORT, self.protocol.create_announce(class_name))
        self.class_name = class_name
        self.bcast.start()

    def multicast(self, machines, num_msgs, bandwidth, type="multicast"):
        """Inicia a captura"""

        # funcoes de socket
        def sock_mcast():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_IP)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s

        def sock_bcast():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_IP)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s

        s = sock_mcast()
        s = connect(z, LISTENPORT, timeout=5)

    def run(self):
        """Starts a background thread"""
        while 1:
            action = self.actions.get()
            if not action:
                continue
            # chegou ALGO
            name, parameters = action
            print "Running %s" % name
            if name == "multicast":
                machines, num_msgs, bandwidth = parameters
                self.multicast(machines, num_msgs, bandwidth, type="broadcast")
            elif name == "quit":
                return
            else:
                print "Unknown action %s" % name
# }}}

# {{{ TeacherGui
class TeacherGui:
    selected_machines = 0
    """Teacher GUI main class"""
    def __init__(self, guifile, service):
        """Initializes the interface"""
        # internal variables
        self.class_name = None
        self.bcast = None
        self.service = service
        self.service.set_gui(self)
        self.new_clients_queue = Queue.Queue()
        # colors
        self.color_normal = gtk.gdk.color_parse("#99BFEA")
        self.color_active = gtk.gdk.color_parse("#FFBBFF")
        self.color_background = gtk.gdk.color_parse("#FFFFFF")

        self.wTree = gtk.glade.XML(guifile)

        # Callbacks
        dic = {
                "on_MainWindow_destroy": self.on_MainWindow_destroy # fecha a janela principal
                }
        self.wTree.signal_autoconnect(dic)

        # tooltips
        self.tooltip = gtk.Tooltips()

        # Muda o background
        self.MainWindow.modify_bg(gtk.STATE_NORMAL, self.color_background)
        self.MachineLayout.modify_bg(gtk.STATE_NORMAL, self.color_background)

        # Configura os botoes
        self.QuitButton.connect('clicked', self.on_MainWindow_destroy)
        self.SelectAllButton.connect('clicked', self.select_all)
        self.UnselectAllButton.connect('clicked', self.unselect_all)
        #self.StartCapture.connect('clicked', self.start_capture)
        #self.StopCapture.connect('clicked', self.stop_capture)
        #self.BandwidthButton.connect('clicked', self.bandwidth)
        #self.MulticastButton.connect('clicked', self.multicast)
        #self.BroadcastButton.connect('clicked', self.multicast, "broadcast")
        #self.AnalyzeButton.connect('clicked', self.analyze)

        # Configura o timer
        gobject.timeout_add(1000, self.monitor)

        # Inicializa a matriz de maquinas
        self.machine_layout = [None] * MACHINES_X
        for x in range(0, MACHINES_X):
            self.machine_layout[x] = [None] * MACHINES_Y

        self.machines = {}

        # Mostra as maquinas
        self.MachineLayout.show_all()

        # inicializa o timestamp
        self.curtimestamp = 0

        # Create some testing machines
        for addr in range(64, 98):
            machine = self.mkmachine("192.168.0.%d" % addr)
            machine.button.connect('clicked', self.cb_machine, machine)
            self.put_machine(machine)
            self.machines[addr] = machine
            machine.show_all()

        self.login()

    def login(self):
        """Asks teacher to login"""
        dialog = gtk.Dialog(_("Login"), self.MainWindow, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(_("Please login"))
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        hbox = gtk.HBox()
        login = gtk.Label(_("Your name (teacher or class name):"))
        hbox.pack_start(login)
        entry_login = gtk.Entry()
        entry_login.set_text(_("My name"))
        hbox.pack_start(entry_login)
        dialog.vbox.pack_start(hbox)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.class_name = entry_login.get_text()
            print "Login: %s" % self.class_name
            dialog.destroy()
            # Starting broadcasting service
            self.service.start_broadcast(self.class_name)
            self.service.server.start()
            return True
        else:
            dialog.destroy()
            return None

    def question(self, title, input=None):
        """Asks a question :)"""
        # cria a janela do dialogo
        dialog = gtk.Dialog(_("Question"), self.MainWindow, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK,
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialogLabel = gtk.Label(title)
        dialog.vbox.add(dialogLabel)
        dialog.vbox.set_border_width(8)
        if input:
            entry = gtk.Entry()
            entry.set_text(input)
            dialog.vbox.add(entry)
        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            dialog.destroy()
            if input:
                return entry.get_text()
            else:
                return True
        else:
            dialog.destroy()
            return None

    def add_client(self, client):
        """Adds a new client"""
        self.new_clients_queue.put(client)

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
        print "Not enough layout space to add a machine!"

    def monitor(self):
        """Monitors new machines connections"""
        #self.StatusLabel.set_markup("<b>Link:</b> %s, <b>Signal:</b> %s, <b>Noise:</b> %s" % (link, level, noise))
        while not self.new_clients_queue.empty():
            addr = self.new_clients_queue.get()
            if addr not in self.machines:
                # Maquina nova
                gtk.gdk.threads_enter()
                machine = self.mkmachine("%s" % addr)
                machine.button.connect('clicked', self.cb_machine, machine)
                self.put_machine(machine)
                self.machines[addr] = machine
                machine.show_all()
                self.StatusLabel.set_text("Found %s (%d machines connected)!" % (addr, len(self.machines)))
                gtk.gdk.threads_leave()
            else:
                machine = self.machines[addr]
                self.tooltip.set_tip(machine, _("Updated on %s" % (time.asctime())))

        gobject.timeout_add(1000, self.monitor)

    def set_offline(self, machine, message=None):
        """Marks a machine as offline"""
        if machine not in self.machines:
            print "Error: machine %s not registered!" % machine
            return
        gtk.gdk.threads_enter()
        self.machines[machine].button.set_image(self.machines[machine].button.img_off)
        if message:
            self.tooltip.set_tip(self.machines[machine], _("%s\%s!") % (time.asctime(), message))
        gtk.gdk.threads_leave()

    def multicast(self, widget, type="multicast"):
        """Inicia transmissao de multicast"""
        print "Bandwidth to estimate: %s Kbps" % (bandwidth)

        machines = []
        for z in self.machines:
            img = self.machines[z].button.get_image()
            if img == self.machines[z].button.img_on:
                machines.append(z)

        self.service.actions.put((type, (machines, num_msgs, bandwidth)))

    def select_all(self, widget):
        """Selects all machines"""
        for z in self.machines.values():
            z.button.set_image(z.button.img_on)

    def unselect_all(self, widget):
        """Selects all machines"""
        for z in self.machines.values():
            z.button.set_image(z.button.img_off)

    def __getattr__(self, attr):
        """Requests an attribute from Glade"""
        obj = self.wTree.get_widget(attr)
        if not obj:
            #bluelab_config.error("Attribute %s not found!" % attr)
            return None
        else:
            return obj

    def on_MainWindow_destroy(self, widget):
        """Main window was closed"""
        print "Here!!"
        gtk.main_quit()
        print "Closing pending threads.."
        self.service.quit()

    def get_img(self, imgpath):
        """Returns image widget if exists"""
        try:
            fd = open(imgpath)
            fd.close()
            img = gtk.Image()
            img.set_from_file(imgpath)
        except:
            img=None
        return img

    def mkmachine(self, name, img="machine.png", img_offline="machine_off.png", status="online"):
        """Creates a client representation"""
        box = gtk.VBox(homogeneous=False)

        imgpath = "iface/%s" % (img)
        imgpath_off = "iface/%s" % (img_offline)

        img = self.get_img(imgpath)
        img_off = self.get_img(imgpath_off)

        button = gtk.Button()
        button.img_on = img
        button.img_off = img_off
        button.machine = name
        if status=="online":
            button.set_image(button.img_on)
        else:
            button.set_image(button.img_off)
        box.pack_start(button, expand=False)

        label = gtk.Label(_("name"))
        label.set_use_markup(True)
        label.set_markup("<small>%s</small>" % name)
        box.pack_start(label, expand=False)

        self.tooltip.set_tip(box, name)
#        box.set_size_request(52, 52)

        # Sets private variables
        box.machine = name
        box.button = button
        box.label = label
        box.wifi = None
        return box

    def cb_machine(self, widget, machine):
        """Callback when clicked on a client machine"""
        img = machine.button.get_image()
        if img == machine.button.img_off:
            machine.button.set_image(machine.button.img_on)
        else:
            machine.button.set_image(machine.button.img_off)

        # muda o texto

    def mkbutton(self, img, img2, text, action, color_normal, color_active):
        """Creates a callable button"""
        box = gtk.HBox(homogeneous=False)
        # Imagem 1
        imgpath = "%s/%s" % (self.appdir, img)
        # Verifica se arquivo existe
        try:
            fd = open(imgpath)
            fd.close()
        except:
            imgpath=None
        if imgpath:
            img = gtk.Image()
            img.set_from_file(imgpath)
            box.pack_start(img, expand=False)

        # Verifica se arquivo existe
        try:
            fd = open(imgpath)
            fd.close()
        except:
            imgpath=None
        if imgpath:
            img2 = gtk.Image()
            img2.set_from_file(imgpath)

        # Texto
        label = gtk.Label(text)
        label.set_use_markup(True)
        label.set_markup("<b>%s</b>" % text)
        box.pack_start(label, expand=False)

        button = gtk.Button()
        button.modify_bg(gtk.STATE_NORMAL, color_normal)
        button.modify_bg(gtk.STATE_PRELIGHT, color_active)

        button.add(box)

        # callback
        if action:
            button.connect('clicked', action, "")
        button.show_all()
        return button
# }}}

if __name__ == "__main__":
    # configura o timeout padrao para sockets
    socket.setdefaulttimeout(2)
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    print _("Starting broadcast..")
    # Main service service
    service = TeacherRunner()
    # Main interface
    gui = TeacherGui("iface/teacher.glade", service)
    service.start()

    print _("Starting main loop..")
    gtk.main()
    gtk.gdk.threads_leave()
