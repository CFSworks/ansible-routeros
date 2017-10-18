#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2017 Sam Edwards
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import re

from ansible.plugins.terminal import TerminalBase
from ansible.errors import AnsibleConnectionFailure


class TerminalModule(TerminalBase):

    terminal_stdout_re = [
        re.compile(br"\[\w+\@[\w\-\.]+\] ?> ?$"),

        re.compile(br"Do you want to see the software license\? \[Y/n\]: ?"),
    ]

    terminal_stderr_re = [
        re.compile(br"\nbad command name"),
        re.compile(br"\nno such item"),
        re.compile(br"\ninvalid value for"),
    ]

    def on_open_shell(self):
        try:
            if 'software license?' in self._connection._last_response:
                self._connection._shell.sendall(' ') # skip without answering
                self._connection.receive()
        except AnsibleConnectionFailure:
            raise AnsibleConnectionFailure('unable to bypass license prompt')
