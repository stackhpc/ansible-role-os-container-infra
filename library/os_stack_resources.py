#!/usr/bin/python
# coding: utf-8 -*-

# Copyright: (c) 2018, Felix Ehrenpfort <felix.ehrenpfort@codecentric.cloud>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: os_stack_resources
short_description: Retrieve a list of resources belonging to a stack within OpenStack
version_added: "2.8"
author: "Bharat Kunwar (bharat@stackhpc.com)"
description:
    - Retrieve list of resources associated with a stack.
notes:
    - Facts are placed in the (openstack_stack_resources) variable.
requirements:
    - "python >= 2.7"
    - "openstacksdk"
options:
    name:
      description:
        - Name of the stack that should be created, name could be char and digit, no space
      required: true
    max_depth:
      description:
        - Maximum recursion depth
      default: 2
      required: false
    filters:
      description:
        - Dictionary of filters to apply to the output.
      required: false
    availability_zone:
      description:
        - Ignored. Present for backwards compatibility
extends_documentation_fragment: openstack
'''

EXAMPLES = '''
---
- name: get stack resources
  os_stack_resources:
    name: "{{ stack_name }}"
    max_depth: 2
    filters:
      resource_type: "OS::Nova::Server"
'''

RETURN = '''

openstack_stack_resources:
    description: has a dictinary of all the openstack resources belonging to a stack
    returned: always, but can be an empty list
    type: complex
    contains:
        id:
            description: Resource ID.
            type: string
            sample: "kube-master"
        logical_resource_id:
            description: Logical Resource ID.
            type: string
            sample: "kube-master"
        physical_resource_id:
            description: Physical Resource ID.
            type: string
            sample: "97a3f543-8136-4570-920e-fd7605c989d6"
        links:
            description: Links to the current Stack.
            type: list of dict
            sample: "[{'href': 'http://foo:8004/v1/7f6a/stacks/test-stack/97a3f543-8136-4570-920e-fd7605c989d6']"
        updated_at:
            description: Time when the resource was updated.
            type: string
            sample: "2016-07-05T17:38:12Z"
        required_by:
            description: List of logical resource names that depend on this resource
            type: list
            sample: [
                    "docker_volume_attach",
                    "master_wait_condition",
                    "enable_cert_manager_api_deployment"
                    ]
        name:
            description: Name of the resource
            type: string
            sample: "test-resource"
        location:
            description: Location of the resource
            type: string
            sample: null
        status:
            description: Status of the resource
            type: string
            sample: "CREATE_COMPLETE"
        status_reason:
            description: Status reason of the resource
            type: string
            sample: "state changed"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec, openstack_module_kwargs, openstack_cloud_from_module
from ansible.module_utils._text import to_native


def main():

    argument_spec = openstack_full_argument_spec(
        name=dict(required=True),
        filters=dict(default={}, type='dict'),
        max_depth=dict(default=2, type='int'),
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    sdk, cloud = openstack_cloud_from_module(module)
    try:
        filters = module.params['filters']
        max_depth = module.params['max_depth']
        def get_children(name, depth):
            resources = []
            if depth > max_depth:
                return resources
            try:
                for r in cloud.orchestration.resources(name):
                    if r:
                        r = r.to_dict()
                        meets_all_conds = True
                        for key, value in filters.iteritems():
                            meets_all_conds = meets_all_conds and r.get(key) == value
                        if meets_all_conds:
                            resources.append(r)
                        resources.extend(get_children(r.get('physical_resource_id'), depth+1))
                return resources
            except sdk.exceptions.ResourceNotFound as e:
                return resources
        
        resources = get_children(name=module.params['name'], depth=0)

        module.exit_json(changed=False, ansible_facts=dict(openstack_stack_resources=resources))

    except sdk.exceptions.OpenStackCloudException as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
