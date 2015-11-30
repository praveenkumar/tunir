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
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


class OpenstackNode(object):
    def __init__(self, USERNAME, ACCESS_ID,
                 AUTH_URL, TENANT_NAME, IMAGE_ID, SIZE_ID,
                 region='us-west-1', keyname='tunir', security_group='ssh'):

        print "Starting an OpenStack based job."
        self.region = region
        cls = get_driver(Provider.OPENSTACK)
        self.driver = cls(USERNAME, ACCESS_ID, ex_force_auth_url=AUTH_URL,
                          ex_force_auth_version='2.0_password',
                          ex_force_service_type='compute',
                          ex_tenant_name=TENANT_NAME, ex_force_service_region=region)
        sizes = self.driver.list_sizes()
        images = self.driver.list_images()
        security_groups = self.driver.ex_list_security_groups()
        self.size = None
        self.image = None
        self.state = 'pending'
        self.failed = False
        self.node = None
        self.ip = None
        print "IMAGE ID {0}, SIZE {1} REGION {2}".format(IMAGE_ID, SIZE_ID, region)
        try:
            self.size = [s for s in sizes if s.id == SIZE_ID][0]
            self.image = [i for i in images if i.id == IMAGE_ID][0]
            self.security = [se for se in security_groups if se.name == security_group][0]
        except Exception as err:
            print err
            self.failed = True
            return
        try:
            self.node = self.driver.create_node(name='tunir_test_node',
                                                image=self.image, size=self.size, ex_keyname=keyname,
                                                ex_security_groups=[self.security, ], )
            # Now we will try for 3 minutes to get an ip.
            for i in range(5):
                time.sleep(30)
                n = self.driver.ex_get_node_details(self.node.id)
                if n.public_ips:
                    self.ip = n.public_ips[0]
                    self.node = n
                    print "Got the IP", self.ip
                    break
            # Now we will wait change the state to running.
            # 0: running
            # 3: pending
            for i in range(5):
                time.sleep(30)
                print "Trying to find the state."
                n = self.driver.ex_get_node_details(self.node.id)
                if n.state == 0:
                    self.node = n
                    self.state = 'running'
                    print "The node is in running state."
                    time.sleep(30)
                    break
                else:
                    print "Nope, not yet."
        except Exception as err:
            print err
        if not self.ip:
            self.failed = True
    def destroy(self):
        print "Now trying to destroy the Openstack node."
        if self.node.destroy():
            print "Successfully destroyed."
        else:
            print "There was in issue in destorying the node."


def openstack_and_run(config):
    """Takes a config object, starts a new Openstack instance, and then returns it.

    :param config: Dictionary

    :returns: OpenstackNode object
    """
    node = OpenstackNode(config['username'], config['access_id'],
                         config['auth_url'], config['tenant_name'],
                         config['image'], config['size_id'], config.get('region', 'us-west-1'),
                         config.get('keyname', 'tunir'), config.get('security_group', 'ssh'))
    if not node.failed:  # Means we have an ip
        config['host_string'] = node.ip
    return node, config
