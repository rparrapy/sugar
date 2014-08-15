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
from sugar3.datastore import datastore

import os
import time
from datetime import timedelta, date
from jarabe.model import shell
from sugarlistens import helper
from gettext import gettext as _
from jarabe.journal import misc
from sugar3.activity import activityfactory


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

_WEEK_DAYS = [_('monday'), _('tuesday'), _('wednesday'), _('thursday'),
              _('friday'), _('saturday'), _('sunday')]


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
        self._bundle_id = None

    def _init_recognizer(self):
        self._recognizer = helper.RecognitionHelper(self._path)
        self._recognizer.listen_to('start (?P<name>\w+)', self._start_activity)
        self._recognizer.listen_to('resume (?P<name>\w+$)', self._resume_activity)
        self._recognizer.listen_to('resume (?P<name>\w+) from (?P<day>\w+)', self._resume_activity)

        self._recognizer.start_listening()
        logging.warning('Starting listener')

    def _start_activity(self, text, pattern, name):
        logging.warning('Voice command: %s' % text)
        registry = bundleregistry.get_registry()
        activity_info = registry.get_bundle(_NAME_TO_ID.get(_(name)))
        # misc.launch(activity_info)

    def _resume_activity(self, text, pattern, name, day=None):
        logging.warning('Voice command: %s' % text)
        logging.warning('Activity: %s' % name)
        logging.warning('Day: %s' % day)

        properties = ['uid', 'title', 'icon-color', 'activity', 'activity_id',
                      'mime_type', 'mountpoint', 'timestamp']

        timestamp = None
        t = date.today()

        if day:
            if _(day) == _('yesterday'):
                delta = -1
            else:
                delta = abs(t.weekday() - _WEEK_DAYS.index(_(day))) - 7

            d = t + timedelta(days=delta)
            n = d + timedelta(days=1)
            start = time.mktime(d.timetuple())
            end = time.mktime(n.timetuple())
            timestamp = {'start': start, 'end':end}

        logging.warning('build query')
        query = {}
        if not _(name) == _('last activity'):
            query['activity'] = _NAME_TO_ID.get(_(name))
        if timestamp:
            query['timestamp'] = timestamp

        #logging.warning(timestamp)
        datastore.find(query, sorting=['+timestamp'],
                   limit=1,
                   properties=properties,
                   reply_handler=self.__get_last_activity_reply_handler_cb,
                   error_handler=self.__get_last_activity_error_handler_cb)

    def __get_last_activity_reply_handler_cb(self, entries, total_count):
        if entries:
            if not entries[0]['activity_id']:
                entries[0]['activity_id'] = activityfactory.create_activity_id()
            misc.resume(entries[0], entries[0]['activity'])


    def __get_last_activity_error_handler_cb(self, error):
        logging.error('Error retrieving most recent activities: %r', error)


    def _test_result(self, text):
        logging.warning('Voice command: %s' % text)


    def __active_activity_changed(self, home_model, home_activity):
        if home_activity and home_activity.get_bundle_id():
            self._recognizer.stop_listening('start (?P<name>\w+)')
            self._recognizer.stop_listening('resume (?P<name>\w+$)')
            self._recognizer.stop_listening('resume (?P<name>\w+) from (?P<day>\w+)')
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
    
