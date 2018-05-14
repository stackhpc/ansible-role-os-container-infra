#!/usr/bin/env python
#
# This script allows a user to create, scale (update)  or get inventory of a
# Magnum cluster. It is essential that a cluster template already exists before
# cluster creation or scaling is requested.
#
# To view warnings emitted by this script, export the following
# following variable before running ansible:
#
#   export ANSIBLE_LOG_PATH=ansible.log
#
# To filter these warnings:
#
#   tail -f ansible.log | grep WARNING

from ansible.module_utils.basic import AnsibleModule
from ansible.utils.display import Display
from heatclient.client import Client
import openstack
import time

display = Display()

class StackFacts(object):
    def __init__(self, **kwargs):
        self.stack_id = kwargs['stack_id']
        self.nested_depth = kwargs['nested_depth']
        self.filter_type = kwargs['filter_type']
    
        self.connect(kwargs['cloud_name'])

    def connect(self, cloud_name):
        self.os_cloud = openstack.connect(cloud=cloud_name)
        self.os_cloud.authorize()
        self.client = Client('1', session=self.os_cloud.session)

    def get(self):
        stack_list = self.client.resources.list(
            stack_id=self.stack_id,
            nested_depth=self.nested_depth,
            type=self.filter_type,
        )
        return [item.to_dict() for item in stack_list]

if __name__ == '__main__':
    module = AnsibleModule(
        argument_spec = dict(
            cloud_name=dict(required=True, type='str'),
            stack_id=dict(required=True, type='str'),
            nested_depth=dict(default=1, type='int'),
            filter_type=dict(default='', type='str'),
        ),
        supports_check_mode=False
    )

    display = Display()

    stack_facts = StackFacts(**module.params)
    result_dict = stack_facts.get()

    module.exit_json(changed=False,stack_facts=result_dict)
