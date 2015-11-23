# -*- coding: utf-8 -*-
"Tunir module to talk to OpenStack"

# Copyright © 2015  Praveen Kumar <kumarpraveen.nitdgp@gmail.com>
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v.2, or (at your option) any later
# version.  This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.  You
# should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

import time
from novaclient.v2 import client as novaclient


class OpenstackNode(object):
    def __init__(self, AUTH_URL, USERNAME, API_KEY, IMAGE_NAME, project_id="tunir",
                 keyname='tunir', security_group='ssh', flavor='m1.small'):

        print "Starting an OpenStack based job."
        self.project = project_id
        self.nova = novaclient.Client(username=USERNAME,
                api_key=API_KEY, auth_url=AUTH_URL,
                project_id=project_id)
        flavors = self.nova.flavors.list()
        images = self.nova.images.list()
        self.flavor = None
        self.image = None
        self.state = 'pending'
        self.failed = False
        self.node = None
        self.ip = None
        print "IMAGE_NAME {0}, FLAVOUR {1} PROJECT {2}".format(IMAGE_NAME, flavor,
                                                             project_id)
        try:
            self.nova.authenticate()
            self.flavor = [s for s in flavors if s.name == flavor][0]
            self.image = [i for i in images if i.name == IMAGE_NAME][0]
        except Exception as err:
            print err
            self.failed = True
            return
        try:
            self.ip = self.nova.floating_ips.create(self.nova.floating_ip_pools.list()[0].name)
            network = self.nova.networks.list()[0]
            self.node = self.nova.servers.create(name='tunir_test_node',
                                                image=self.image,
                                                flavor=self.flavor,
                                                nics=[{'net-id':network.id}],
                                                key_name = keyname,
                                                security_groups=[security_group, ], )

            # Now we will wait change the state to running.
            # 0: running
            # 3: pending
            for i in range(5):
                time.sleep(30)
                print "Trying to find the state."
                node = self.nova.servers.find(id=self.node.id)
                if node.state == 'Active':
                    self.node = node
                    self.state = 'running'
                    print "The node is in running state."
                    time.sleep(30)
                    break
                else:
                    print "Nope, not yet."

            # Add floating ip
            node.add_floating_ip(self.ip)

        except Exception as err:
            print err
        if not self.ip:
            self.failed = True

    def destroy(self):
        print "Now trying to destroy the OpenstackNode node."
        self.ip.delete()
        if not self.node.delete():
            print "Successfully destroyed."
        else:
            print "There was in issue in destorying the node."


def openstack_and_run(config):
    """Takes a config object, starts a new openstack instance, and then returns it.

    :param config: Dictionary

    :returns: Openstack object
    """
    node = OpenstackNode(config['auth_url'], config['username'],
                   config['api_key'], config['image_name'],
                   config.get('project_id', 'tunir'),
                   config.get('keyname', 'tunir'), config.get('security_group', 'ssh'),
                   config.get('flavor', 'm1.small'))
    if not node.failed:  # Means we have an ip
        config['host_string'] = node.ip.ip
    return node, config
