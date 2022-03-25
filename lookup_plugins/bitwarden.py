#!/usr/bin/env python

# (c) 2018, Matt Stofko <matt@mjslabs.com>
# GNU General Public License v3.0+ (see LICENSE or
# https://www.gnu.org/licenses/gpl-3.0.txt)
#
# This plugin can be run directly by specifying the field followed by a list of
# entries, e.g.  bitwarden.py password google.com wufoo.com
#
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import os
import sys

from subprocess import Popen, PIPE, STDOUT, check_output

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


DOCUMENTATION = """
lookup: bitwarden
author:
  - Matt Stofko <matt@mjslabs.com>
requirements:
  - bw (command line utility)
  - BW_SESSION environment var (from `bw login` or `bw unlock`)
short_description: look up data from a bitwarden vault
description:
  - use the bw command line utility to grab one or more items stored in a
    bitwarden vault
options:
  _terms:
    description: name of item that contains the field to fetch
    required: true
field:
  description: 
   - field to return from bitwarden (item, username, password, uri, totp, notes, exposed, attachment, folder, collection, org-collection, organization, template, fingerprint, send)
   - if field is no bitwarden field, then every field from `bw get item <term>` as json can be read. eg field=fields.some_custom_field or field=id
  default: 'password'

sync:
  description: If True, call `bw sync` before lookup
"""

EXAMPLES = """
- name: get 'username' from Bitwarden entry 'Google'
  debug:
    msg: "{{ lookup('bitwarden', 'Google', field='username') }}"
"""

RETURN = """
  _raw:
    description:
      - Items from Bitwarden vault
"""


class Bitwarden(object):
    def __init__(self, path):
        self._cli_path = path
        self._bw_session = ""
        try:
            check_output([self._cli_path, "--version"])
        except OSError:
            raise AnsibleError("Command not found: {0}".format(self._cli_path))

    @property
    def session(self):
        return self._bw_session

    @session.setter
    def session(self, value):
        self._bw_session = value

    @property
    def cli_path(self):
        return self._cli_path

    @property
    def logged_in(self):
        # Parse Bitwarden status to check if logged in
        if self.status() == 'unlocked':
            return True
        else:
            return False

    def _run(self, args):
        my_env = os.environ.copy()
        if self.session != "":
            my_env["BW_SESSION"] = self.session
        p = Popen([self.cli_path] + args, stdin=PIPE,
                  stdout=PIPE, stderr=STDOUT, env=my_env)
        out, _ = p.communicate()
        out = out.decode()
        rc = p.wait()
        if rc != 0:
            display.debug("Received error when running '{0} {1}': {2}"
                          .format(self.cli_path, args, out))
            if out.startswith("Vault is locked."):
                raise AnsibleError("Error accessing Bitwarden vault. "
                                   "Run 'bw unlock' to unlock the vault.")
            elif out.startswith("You are not logged in."):
                raise AnsibleError("Error accessing Bitwarden vault. "
                                   "Run 'bw login' to login.")
            elif out.startswith("Failed to decrypt."):
                raise AnsibleError("Error accessing Bitwarden vault. "
                                   "Make sure BW_SESSION is set properly.")
            elif out.startswith("Not found."):
                raise AnsibleError("Error accessing Bitwarden vault. "
                                   "Specified item not found: {}".format(args[-1]))
            else:
                raise AnsibleError("Unknown failure in 'bw' command: "
                                   "{0}".format(out))
        return out.strip()

    def sync(self):
        self._run(['sync'])

    def status(self):
        try:
            data = json.loads(self._run(['status']))
        except json.decoder.JSONDecodeError as e:
            raise AnsibleError("Error decoding Bitwarden status: %s" % e)
        return data['status']

    def get_entry(self, key, field, organizationId, collectionId):
        try: 
            return self._run(["get", field, key])
        except AnsibleError as err:
            if "More than one result was found." in err.message:
                # find first in the organisation and collection
                allData = json.loads(self._run(["list", "items", "--search", key]))
                firstFound = False
                for data in allData:
                    if data['name'] != key:
                        continue
                    if collectionId is not None and not (collectionId in data['collectionIds']):
                        continue
                    if organizationId is not None and data['organizationId'] != organizationId:
                        continue
                    firstFound = True
                    break
                if (firstFound and (collectionId is not None or organizationId is not None)):
                    return self.get_entry(data['id'], field, organizationId, collectionId)
                else:
                    raise AnsibleError("no item='%s' in organization and/or collection found" % (key))
            else:
                # field was no bitwarden <object>
                item = json.loads(self.get_entry(key, 'item', organizationId, collectionId))
                if organizationId is not None and item['organizationId'] != organizationId:
                    raise AnsibleError("no item='%s' in organization found" % (key))
                if collectionId is not None and not (collectionId in item['collectionIds']):
                    raise AnsibleError("no item='%s' in collection found" % (key))

            splitted = field.split(".")
            for v in splitted:
                if isinstance(item, dict) and (v in item):
                    item = item[v]
                elif isinstance(item, list):
                    if (splitted[0] == "fields"):
                        filtered = filter(lambda oneItem: ('name' in oneItem) and oneItem['name']==v, item)
                        return list(map(lambda oneItem: oneItem['value'], filtered))
                    else:
                        if isinstance(item[0], dict):
                            item = list(map(lambda oneItem: oneItem[v], item))
                        else:
                            return item
                else:
                    return item
            return item

    def get_attachments(self, key, itemid, output, filename, organizationId, collectionId):
        attachmentArray = ['get', 'attachment', 
            '{}'.format(key), 
            '--output={}{}'.format(output, filename), 
            '--itemid={}'.format(itemid)]
        return self._run(attachmentArray)


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        bw = Bitwarden(path=kwargs.get('path', 'bw'))

        if not bw.logged_in:
            raise AnsibleError("Not logged into Bitwarden: please run "
                               "'bw login', or 'bw unlock' and set the "
                               "BW_SESSION environment variable first")

        field = kwargs.get('field', 'password')
        organizationId = kwargs.get('organizationId')
        collectionId = kwargs.get('collectionId')
        values = []

        if kwargs.get('sync'):
            bw.sync()
        if kwargs.get('session'):
            bw.session = kwargs.get('session')

        for term in terms:
            if 'attachments' in kwargs:
                itemid = term
                attachments = kwargs.get('attachments')
                output = kwargs.get('output', term)
                if isinstance(attachments, list):
                    for attachment in attachments:
                        if (output.endswith('/')):
                            values.append(bw.get_attachments(attachment, itemid, output, attachment, organizationId, collectionId))
                        else:
                            values.append(bw.get_attachments(attachment, itemid, output+"/", attachment, organizationId, collectionId))
                else:
                    if (output.endswith('/')):
                        values.append(bw.get_attachments(attachments, itemid, output, attachments, organizationId, collectionId))
                    else:
                        values.append(bw.get_attachments(attachments, itemid, output, "", organizationId, collectionId))
            else:
                values.append(bw.get_entry(term, field, organizationId, collectionId))
        return values


def main():
    if len(sys.argv) < 3:
        print("Usage: {0} <field> <name> [name name ...]".format(os.path.basename(__file__)))
        print("Usage: {0} <json-lookup> <name> [name name ...]".format(os.path.basename(__file__)))
        print('example: bitwarden.py \'{"field":"fields.testuser"}\' "<name>"')
        return -1
    try:
        options = json.loads(sys.argv[1])
    except json.decoder.JSONDecodeError as err:
        options = { "field": sys.argv[1] }
    print(LookupModule().run(sys.argv[2:], None, **options))

    return 0


if __name__ == "__main__":
    sys.exit(main())
