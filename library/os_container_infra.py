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
module: os_container_infra
short_description: Create, update and delete container infra.
author: bharat@stackhpc.com
version_added: "1.0"
description:
    -  Create, update and delete container infra using Openstack Magnum API.
notes:
    - This module creates a new top-level C(container_infra) fact, which
      contains information about Magnum container infrastructure.
requirements:
    - "python >= 2.6"
    - "openstacksdk"
    - "python-magnumclient"
options:
   cloud:
     description:
       - Cloud name inside cloud.yaml file.
     type: str
   state:
     description:
       - Must be `present`, `query` or `absent`.
     type: str
   cluster_name:
     description:
        - Magnum cluster name or uuid.
     type: str
   cluster_template_name:
     description:
        - Magnum cluster template name or uuid.
     type: str
   master_count:
     description:
        - Number of master nodes.
     type: int
     default: 1
   node_count:
     description:
        - Number of worker nodes.
     type: int
     default: 1
   keypair:
     description:
        - Keypair name or uuid to use for authentication.
     type: str
extends_documentation_fragment: openstack
'''

EXAMPLES = '''
# Gather facts about all resources under <stack_id>:
- os_container_infra:
    cloud: mycloud
    state: present
    cluster_name: test-cluster
    cluster_template_name: swarm-fedora-atomic-27
    master_count: 1
    node_count: 1
    keypair: default
- debug:
    var: container_infra
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.utils.display import Display
from magnumclient.client import Client
from magnumclient.exceptions import *
import openstack
import time

class WaitCondition(Exception):
    pass

class OpenStackError(Exception):
    pass

class OpenStackAuthConfig(Exception):
    pass

class ContainerInfra(object):
    def __init__(self, **kwargs):
        self.name = kwargs['cluster_name']
        self.master_count = kwargs['master_count']
        self.node_count = kwargs['node_count']
        self.keypair = kwargs['keypair']
        self.state = kwargs['state'].lower()

        self.connect(**kwargs)
        self.cluster_template_id = self.client.cluster_templates.get(kwargs['cluster_template_name']).uuid
        
        self.result = dict()

    def connect(self, **kwargs):
        if kwargs['auth_type'] == 'password':
            if kwargs['cloud']:
                self.cloud = openstack.connect(cloud=kwargs['cloud'])
            elif kwargs['auth']:
                self.cloud = openstack.connect(**kwargs['auth'])
            else:
                self.cloud = openstack.connect()
        else:
            raise OpenStackAuthConfig('Only `password` auth_type is supported.')
        self.cloud.authorize()
        self.client = Client('1', endpoint_override=False, session=self.cloud.session)

    def apply(self):
        timeout = 3600
        start = time.time()
        changed = False
        while True:
            try:
                # Get cluster info or raise WaitCondition if a new one is created.
                try:
                    self.result = self.client.clusters.get(self.name).to_dict()
                    if self.state == 'query':
                        return changed
                except NotFound as e:
                    # Create new cluster here if no cluster with the name was found
                    if self.state == 'present':
                        self.create()
                    elif self.state in ['absent']:
                        return changed
                    else:
                        raise(e)
                status = self.result['status']
                # If the cluster is in a failed status, raise error:
                if status.endswith('FAILED'):
                    raise OpenStackError(self.result['faults'])
                # If the cluster creation and update is in progress:
                elif status.endswith('PROGRESS'):
                    raise WaitCondition(status)
                # Since the cluster looks ready, raise a WaitCondition if cluster is updated.
                elif status.endswith('COMPLETE'):
                    self.update()
                    return changed
                # This should never be the case but just in case, lets try and catch it.
                else:
                    raise OpenStackError(self.result['faults'])
            except WaitCondition as e:
                now = time.time()
                if now > start + timeout:
                    # This is taking far too long, terminate.
                    raise OpenStackError("Timed out waiting for creation after {} seconds.".format(timeout))
                else:
                    # Wait before trying again.
                    display.debug('[DEBUG] Waited {}/{} seconds {}'.format(now - start, timeout, e))
                    time.sleep(10)
                    changed = True

    def create(self):
        # Create a cluster with parameters initialised with
        self.client.clusters.create(
            name=self.name,
            cluster_template_id=self.cluster_template_id,
            master_count=self.master_count,
            node_count=self.node_count,
            keypair=self.keypair
        )
        raise WaitCondition("Cluster called {} does not exist, creating new.".format(self.name))

    def update(self):
        # Raise module error if there is a mismatch between cluster template ids
        cluster_template_mismatch = self.cluster_template_id != self.result['cluster_template_id']
        if cluster_template_mismatch:
            raise ValueError("Cluster's current template name does not match provided template name.")

        if self.state == 'present':
            # Patch list to append list of patches
            patch_list = list()

            # Update number of masters if there is a mismatch
            master_count_mismatch = self.master_count != self.result['master_count']
            if master_count_mismatch:
                patch = dict(op='replace', value=self.master_count, path='/master_count')
                patch_list.append(patch)

            # Update number of nodes if there is a mismatch
            node_count_mismatch = self.node_count != self.result['node_count']
            if node_count_mismatch:
                patch = dict(op='replace', value=self.node_count, path='/node_count')
                patch_list.append(patch)

            # There appears to be a patch needed to apply
            if len(patch_list) > 0:
                self.client.clusters.update(self.result['uuid'], patch_list)
                raise WaitCondition("Applying patch to the cluster: {}".format(patch_list))

        # Since the cluster exists but the requested state is absent, delete the cluster
        elif self.state == 'absent':
            self.client.clusters.delete(self.result['uuid'])
            raise WaitCondition("Deleting cluster: {}".format(self.result['uuid']))
        
if __name__ == '__main__':
    module = AnsibleModule(
        argument_spec = dict(
            cloud=dict(required=False, type='str'),
            auth=dict(required=False, type='dict'),
            auth_type=dict(default='password', required=False, type='str'),
            state=dict(default='present', choices=['present','absent', 'query']),
            cluster_name=dict(required=True, type='str'),
            cluster_template_name=dict(required=True, type='str'),
            master_count=dict(required=True, type='int'),
            node_count=dict(required=True, type='int'),
            keypair=dict(required=True, type='str'),
        ),
        supports_check_mode=False
    )

    display = Display()

    container_infra = ContainerInfra(**module.params)

    try:
        changed = container_infra.apply()
    except Exception as e:
        module.fail_json(msg=repr(e))

    module.exit_json(changed=changed, ansible_facts=dict(container_infra=container_infra.result))
