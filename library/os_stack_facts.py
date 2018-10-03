#!/usr/bin/env python
#
# Copyright (c) 2018 StackHPC Ltd.
# Apache 2 Licence

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: os_stack_facts
short_description: Retrieve facts about stack resources
author: bharat@stackhpc.com
version_added: "1.0"
description:
    - Retrieve facts about stack resources from OpenStack Heat API.
notes:
    - This module creates a new top-level C(stack_facts) fact, which
      contains a list of stack resources.
requirements:
    - "python >= 2.6"
    - "openstacksdk"
    - "python-heatclient"
options:
   cloud:
     description:
       - Cloud name inside cloud.yaml file.
     type: str
   stack_id:
     description:
        - Heat stack name or uuid.
     type: str
   nested_depth:
     description:
        - Number of levels to recurse into stack resources.
     type: int
     default: 1
   filters:
     description:
        - Filters to apply when returning results. Valid fields are
          (parent_resource, resource_name, links, logical_resource_id,
          creation_time, resource_status, updated_time, required_by,
          resource_status_reason, physical_resource_id, resource_type).
     type: list of str
extends_documentation_fragment: openstack
'''

EXAMPLES = '''
# Gather facts about all resources under <stack_id>:
- os_stack_facts:
    cloud: mycloud
    stack_id: xxxxx-xxxxx-xxxx-xxxx
    nested_depth: 4
    filters:
      resource_type: OS::Nova::Server
- debug:
    var: stack_facts
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.utils.display import Display
from heatclient.client import Client
import openstack
import time

display = Display()

class OpenStackAuthConfig(Exception):
    pass

class StackFacts(object):
    def __init__(self, **kwargs):
        self.stack_id = kwargs['stack_id']
        self.nested_depth = kwargs['nested_depth']
        self.filters = kwargs['filters']
        self.connect(**kwargs)

    def connect(self, **kwargs):
        if kwargs['auth_type'] == 'environment':
            self.cloud = openstack.connect()
        elif kwargs['auth_type'] == 'cloud':
            self.cloud = openstack.connect(cloud=kwargs['cloud'])
        elif kwargs['auth_type'] == 'password':
            self.cloud = openstack.connect(**kwargs['auth'])
        else:
            raise OpenStackAuthConfig('Provided auth_type must be one of [environment, cloud, password].')

        self.client = Client('1', session=self.cloud.session)

    def get(self):
        stack_list = self.client.resources.list(
            stack_id=self.stack_id,
            nested_depth=self.nested_depth,
        )
        result = list()
        for item in stack_list:
            item_dict = item.to_dict()
            condition = True
            for k,v in self.filters.items():
                condition = condition and item_dict[k] == v
            if condition:
                result.append(item_dict)
        return result

if __name__ == '__main__':
    module = AnsibleModule(
        argument_spec = dict(
            cloud=dict(required=False, type='str'),
            auth=dict(required=False, type='dict'),
            auth_type=dict(default='environment', required=False, type='str'),
            stack_id=dict(required=True, type='str'),
            nested_depth=dict(default=1, type='int'),
            filters=dict(default=dict(), type='dict'),
        ),
        supports_check_mode=False
    )

    display = Display()

    try:
        stack_facts = StackFacts(**module.params)
    except Exception as e:
        module.fail_json(repr(e))
    module.exit_json(changed=False,ansible_facts=dict(stack_facts=stack_facts.get()))
