# Copyright (C) 2014 Rodrigo Parra
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
from gi.repository import GLib
from gi.repository import Gtk

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model import bundleregistry
from sugar3 import profile
from sugar3.graphics.palette import Palette
from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.icon import Icon
from sugar3.graphics import style
import os
from jarabe.journal import misc
from jarabe.model import shell
from sugarlistens import helper
from gettext import gettext as _
from subprocess import call
import dbus

import logging
_logger = logging.getLogger('SpeechRecognizerView')


_ICON_NAME = 'listen'
_NAME_TO_ID = {
    _('maze'): 'vu.lux.olpc.Maze',
    _('write'): 'org.laptop.AbiWordActivity',
    _('browse'): 'org.laptop.WebActivity',
    _('chat'): 'org.laptop.Chat',
    _('speak'): 'org.laptop.AbiWordActivity',
    _('memorize'): 'org.laptop.AbiWordActivity',
    _('ruler'): 'org.laptop.AbiWordActivity',
    _('read'): 'org.laptop.sugar.ReadActivity',
    _('turtle'): 'org.laptop.TurtleArtActivity'
}


class SpeechRecognizerView(TrayIcon):
    def __init__(self):
        self._color = profile.get_color()
        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=self._color)
        self._MAX_ATTEMPS = 10  # attemps to connect to asr service
        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.props.toggle_palette = True
        self._path = os.path.dirname(os.path.abspath(__file__))
        self._muted = False
        self._init_recognizer()
        self._active = True
        self._home_model = shell.get_model()
        self._home_model.connect('active-activity-changed',
                                 self.__active_activity_changed)

    def _command_result(self, text, pattern, name):
        logging.warning('Voice command: %s' % name)
        registry = bundleregistry.get_registry()
        activity_info = registry.get_bundle(_NAME_TO_ID.get(_(name)))
        if activity_info:
            misc.launch(activity_info)

    def _init_recognizer(self):
        GLib.idle_add(self.__connection_attemp_cb, self)

    def __connection_attemp_cb(self, view):
        try:
            logging.warning('Starting listener')
            view._recognizer = helper.RecognitionHelper(self._path)
            view._recognizer.listen_to('start (?P<name>\w+)',
                                       view._command_result)

            if not view.is_muted():
                view._recognizer.start_listening()
            logging.warning('Listening...')
            return False
        except dbus.DBusException:
            return True

    def __active_activity_changed(self, home_model, home_activity):
        if home_activity:
            activity_info = home_activity._activity_info
        else:
            activity_info = None

        if activity_info and activity_info.get_bundle_id():
            self._recognizer.stop_listening('start (?P<name>\w+)')
            self._active = False
            logging.warning('Stopping listener')
        else:
            if not self._active:
                logging.warning('Back to Home!')
                self._init_recognizer()
                self._active = True

    def create_palette(self):
        label = GLib.markup_escape_text(_('Listen'))
        palette = SpeechRecognizerPalette(label, view=self)
        palette.set_group_id('frame')
        return palette

    def is_muted(self):
        return self._muted

    def set_muted(self, muted):
        self._muted = muted

    def is_active(self):
        return self._active

    def update_icon(self):
        icon_name = 'listen'

        if self.is_muted():
            icon_name = 'listen-muted'
        self.icon.props.icon_name = icon_name


class SpeechRecognizerPalette(Palette):
    def __init__(self, primary_text, view):
        Palette.__init__(self, label=primary_text)
        self._recognizer = view._recognizer
        self._view = view

        self._ok_icon = Icon(icon_name='dialog-ok',
                             icon_size=Gtk.IconSize.MENU)
        self._cancel_icon = Icon(icon_name='dialog-cancel',
                                 icon_size=Gtk.IconSize.MENU)

        label = Gtk.Label()
        label.set_label(_('Mute'))
        align = Gtk.Alignment(xalign=0.0, yalign=0.5, xscale=0.0, yscale=0.0)
        align.add(label)
        button = Gtk.Button()
        button.set_image(self._cancel_icon)
        button.connect('clicked', self.__button_clicked_cb)
        self._asr_label = label
        self._asr_button = button

        hbox = Gtk.HBox()
        hbox.pack_start(align, expand=True, fill=True,
                        padding=style.DEFAULT_PADDING)
        hbox.pack_start(button, expand=False, fill=False,
                        padding=style.DEFAULT_PADDING)
        vbox = Gtk.VBox()

        vbox.pack_start(hbox, True, True, style.DEFAULT_PADDING)
        self.set_content(vbox)
        vbox.show_all()

    def __button_clicked_cb(self, button):
        muted = not self._view.is_muted()
        view = self._view
        view.set_muted(muted)
        label = self._asr_label

        if muted:
            logging.warning('stopping speech recognition pipeline')
            label.set_label(_('Listen'))
            button.set_image(self._ok_icon)
            self._recognizer.stop_pipeline()
        else:
            logging.warning('starting speech recognition pipeline')
            label.set_label(_('Mute'))
            button.set_image(self._cancel_icon)
            if view.is_active():
                self._recognizer.start_listening()
            self._recognizer.resume_pipeline()
        self._view.update_icon()


def start_systemd_service():
    return call(['systemctl', '--user', 'start', 'sugarlistens'])


def setup(tray):
    start_systemd_service()
    tray.add_device(SpeechRecognizerView())
