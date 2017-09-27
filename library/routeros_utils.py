#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2017 Sam Edwards
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

# NOTE: This is not a module. This becomes ansible.module_utils.routeros if
# merged into the Ansible codebase.


try:
    import librouteros
    HAS_LIB = True
except ImportError:
    HAS_LIB = False

import json

from ansible.module_utils._text import to_text
from ansible.module_utils.network_common import to_list, ComplexList
from ansible.module_utils.basic import env_fallback
from ansible.module_utils.six import iteritems
from ansible.module_utils.connection import exec_command

routeros_provider_spec = {
    'host': dict(),
    'port': dict(type='int'),

    'username': dict(fallback=(env_fallback, ['ANSIBLE_NET_USERNAME'])),
    'password': dict(fallback=(env_fallback, ['ANSIBLE_NET_PASSWORD']), no_log=True),
    'ssh_keyfile': dict(fallback=(env_fallback, ['ANSIBLE_NET_SSH_KEYFILE']), type='path'),

    'use_ssl': dict(type='bool'),
    'validate_certs': dict(type='bool'),

    'timeout': dict(type='int'),

    'transport': dict(default='cli', choices=['cli', 'api'])
}
routeros_argument_spec = {
    'provider': dict(type='dict', options=routeros_provider_spec),
}
routeros_top_spec = {
    'host': dict(removed_in_version=2.9),
    'port': dict(removed_in_version=2.9, type='int'),

    'username': dict(removed_in_version=2.9, fallback=(env_fallback, ['ANSIBLE_NET_USERNAME'])),
    'password': dict(removed_in_version=2.9,
                     fallback=(env_fallback, ['ANSIBLE_NET_PASSWORD']), no_log=True),
    'ssh_keyfile': dict(removed_in_version=2.9,
                        fallback=(env_fallback, ['ANSIBLE_NET_SSH_KEYFILE']), type='path'),

    'use_ssl': dict(removed_in_version=2.9, type='bool'),
    'validate_certs': dict(removed_in_version=2.9, type='bool'),

    'timeout': dict(removed_in_version=2.9, type='int'),

    'transport': dict(removed_in_version=2.9, choices=['cli', 'api'])
}
routeros_argument_spec.update(routeros_top_spec)


def load_params(module):
    provider = module.params.get('provider') or dict()
    for key, value in iteritems(provider):
        if key in routeros_provider_spec:
            if module.params.get(key) is None and value is not None:
                module.params[key] = value


_DEVICE_CONNECTION = None

def get_connection(module):
    # pylint: disable=global-statement
    global _DEVICE_CONNECTION
    if not _DEVICE_CONNECTION:
        load_params(module)
        if is_api(module):
            conn = Api(module)
        else:
            conn = Cli(module)
        _DEVICE_CONNECTION = conn
    return _DEVICE_CONNECTION


def is_api(module):
    transport = module.params['transport']
    provider_transport = (module.params['provider'] or {}).get('transport')
    return 'api' in (transport, provider_transport)


def cli_to_api(command):
    """Takes a RouterOS CLI command (like "/system identity set name=foo")
    and yields the librouteros command dict
    (like {"cmd": "/system/identity/set", "name": "foo"})
    """

    # Strip off preceding '/' if present
    if command.startswith('/'):
        command = command[1:]

    # Figuring out where the command ends and where the attributes begin is
    # tough; the command's "verb" actually appears in the middle of the command
    # statement, but right before any attributes, which are USUALLY (but not
    # always) key=value pairs.
    #
    # So, we'll look for either a recognized verb, or a '=' signifying an
    # attribute
    KNOWN_VERBS = frozenset([
        'add', 'cancel', 'comment', 'disable', 'downgrade', 'edit', 'enable',
        'export', 'find', 'get', 'getall', 'listen', 'print', 'remove', 'set',
        'uninstall', 'unschedule', 'upgrade'
    ])

    split_command = command.split()

    verb_index = -1
    for i, word in enumerate(split_command):
        if word in KNOWN_VERBS:
            verb_index = i
            break
        elif '=' in word:
            verb_index = i - 1
            break

    # We now know the command
    cmd = '/'.join([''] + split_command[:verb_index] + [split_command[verb_index]])

    attributes = {}
    for attribute in split_command[verb_index + 1:]:
        if '=' in attribute:
            k, v = attribute.split('=', 1)
        else:
            k = attribute
            v = None

        attributes[k] = v

    attributes['cmd'] = cmd
    return attributes

class Cli:

    def __init__(self, module):
        self._module = module

    def exec_command(self, command):
        if isinstance(command, dict):
            command = self._module.jsonify(command)
        return exec_command(self._module, command)

    def run_commands(self, commands, check_rc=True):
        """Run list of commands on remote device and return results
        """
        responses = list()

        for item in to_list(commands):
            cmd = item['command']

            rc, out, err = self.exec_command(cmd)
            out = to_text(out, errors='surrogate_then_replace')
            if check_rc and rc != 0:
                self._module.fail_json(msg=to_text(err, errors='surrogate_then_replace'))

            try:
                out = self._module.from_json(out)
            except ValueError:
                out = str(out).strip()

            responses.append(out)
        return responses


class Api:

    def __init__(self, module):
        self._module = module

        username = self._module.params['username']
        password = self._module.params['password']

        host = self._module.params['host']
        port = self._module.params['port']

        timeout = self._module.params['timeout']

        if not HAS_LIB:
            self._module.fail_json(
                msg="RouterOS API support requires `librouteros` " +
                "Python package - pip install librouteros")
        else:
            self._api = librouteros.connect(host=host, port=port, username=username,
                                            password=password, timeout=timeout)

    def exec_command(self, cmd):
        api_cmd = cli_to_api(cmd)

        try:
            results = self._api(**api_cmd)
        except librouteros.exceptions.LibError as e:
            return 1, '', e.message

        return 0, json.dumps(results), ''


    def run_commands(self, commands, check_rc=True):
        """Run list of commands on remote device and return results
        """
        responses = list()

        for item in to_list(commands):
            cmd = item['command']

            rc, out, err = self.exec_command(cmd)
            out = to_text(out, errors='surrogate_then_replace')
            if check_rc and rc != 0:
                self._module.fail_json(msg=to_text(err, errors='surrogate_then_replace'))

            try:
                out = self._module.from_json(out)
            except ValueError:
                out = str(out).strip()

            responses.append(out)

        return responses


def to_command(module, commands):
    if is_api(module):
        default_output = 'json'
    else:
        default_output = 'text'

    transform = ComplexList(dict(
        command=dict(key=True),
        output=dict(default=default_output),
        prompt=dict(),
        answer=dict()
    ), module)

    commands = transform(to_list(commands))

    return commands


def run_commands(module, commands, check_rc=True):
    conn = get_connection(module)
    return conn.run_commands(to_command(module, commands), check_rc)
