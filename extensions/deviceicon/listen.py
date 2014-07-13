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
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.tray import TrayIcon
import os
from jarabe.journal import misc
from jarabe.model import shell
from sugarlistens import helper
from gettext import gettext as _

import logging
_logger = logging.getLogger('SpeechRecognizerView')


_ICON_NAME = 'battery'
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
        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.props.toggle_palette = True
        self._path = os.path.dirname(os.path.abspath(__file__))
        self._init_recognizer()
        self._active = True
        self._home_model = shell.get_model()
        self._home_model.connect('active-activity-changed',
                                 self.__active_activity_changed)

    def _init_recognizer(self):
        self._recognizer = helper.RecognitionHelper(self._path)
        self._recognizer.listen_to('start (?P<name>\w+)', self._command_result)
        self._recognizer.start_listening()
        logging.warning('Starting listener')

    def _command_result(self, text, pattern, name):
        logging.warning('Voice command: %s' % name)
        registry = bundleregistry.get_registry()
        activity_info = registry.get_bundle(_NAME_TO_ID.get(_(name)))
        #misc.launch(activity_info)

    def _test_result(self, text):
        logging.warning('Voice command: %s' % text)

    def __active_activity_changed(self, home_model, home_activity):
        if home_activity and home_activity.get_bundle_id():
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
        palette = SpeechRecognizerPalette(label, recognizer=self._recognizer)
        palette.set_group_id('frame')
        return palette


class SpeechRecognizerPalette(Palette):
    def __init__(self, primary_text, recognizer):
        Palette.__init__(self, label=primary_text)
        self._recognizer = recognizer

        box = PaletteMenuBox()
        self.set_content(box)
        box.show()

        pitch_label = Gtk.Label(_('Sugar is listening...'))
        box.append_item(pitch_label, vertical_padding=0)
        pitch_label.show()


def setup(tray):
    tray.add_device(SpeechRecognizerView())
    
