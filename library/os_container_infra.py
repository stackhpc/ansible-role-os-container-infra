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
#   export ANSIBLE_DEBUG=1
#
# To filter these warnings:
#
#   tail -f ansible.log | grep WARNING

from ansible.module_utils.basic import AnsibleModule
from ansible.utils.display import Display
from magnumclient.client import Client as MagnumClient
from magnumclient.exceptions import *
import openstack
import time

class WaitCondition(Exception):
    pass

class OpenStackError(Exception):
    pass

class ContainerInfra(object):
    def __init__(self, **kwargs):
        self.name = kwargs['cluster_name']
        self.master_count = kwargs['master_count']
        self.node_count = kwargs['node_count']
        self.keypair = kwargs['keypair']
        self.state = kwargs['state'].lower()

        self.connect(kwargs['cloud_name'])
        self.cluster_template_id = self.magnum_client.cluster_templates.get(kwargs['cluster_template_name']).uuid
        
        self.result = None
        self.result_dict = dict()

    def connect(self, cloud_name):
        self.os_cloud = openstack.connect(cloud=cloud_name)
        self.os_cloud.authorize()
        self.magnum_client = MagnumClient('1', endpoint_override=False, session=self.os_cloud.session)

    def get(self):
        tries = 0
        fail_after = 100
        changed = False
        while True:
            try:
                # Get cluster info or raise WaitCondition if a new one is created.
                try:
                    result = self.magnum_client.clusters.get(self.name)
                    self.result = result
                    self.result_dict = result.to_dict()
                except NotFound as e:
                    # Create new cluster here if no cluster with the name was found
                    if self.state == 'present':
                        self.create()
                    elif self.state == 'absent':
                        return changed
                # If the cluster is in a failed status, raise error:
                if result.status.endswith('FAILED'):
                    raise OpenStackError("Cluster is not usable because: {}.".format(result.faults))
                # If the cluster creation and update is in progress:
                elif result.status.endswith('PROGRESS'):
                    raise WaitCondition(result.status)
                # Since the cluster looks ready, raise a WaitCondition if cluster is updated.
                elif result.status.endswith('COMPLETE'):
                    self.update()
                    return changed
                # This should never be the case but just in case, lets try and catch it.
                else:
                    raise OpenStackError("Cluster returned unexpected status: {}".format(result.status))
            except WaitCondition as e:
                # This is taking far too long, terminate.
                if fail_after < tries:
                    raise OpenStackError("Failing after {} tries.".format(fail_after))
                # Wait before trying again.
                else:
                    display.debug('[DEBUG] Tries: [{}/{}] {}'.format(tries, fail_after, e))
                    time.sleep(10)
                    tries += 1
                    changed = True

    def create(self):
        # Create a cluster with parameters initialised with
        self.magnum_client.clusters.create(
            name=self.name,
            cluster_template_id=self.cluster_template_id,
            master_count=self.master_count,
            node_count=self.node_count,
            keypair=self.keypair
        )
        raise WaitCondition("Cluster called {} does not exist, creating new.".format(self.name))

    def update(self):
        # Get result if it hasnt been queried yet
        if self.result == None:
            self.get()
        
        # Raise module error if there is a mismatch between cluster template ids
        cluster_template_mismatch = self.cluster_template_id != self.result.cluster_template_id 
        if cluster_template_mismatch:
            raise ValueError("Cluster's current template name does not match provided template name.")

        if self.state == 'present':
            # Patch list to append list of patches
            patch_list = list()

            # Update number of masters if there is a mismatch
            master_count_mismatch = self.master_count != self.result.master_count
            if master_count_mismatch:
                patch = dict(op='replace', value=self.master_count, path='/master_count')
                patch_list.append(patch)

            # Update number of nodes if there is a mismatch
            node_count_mismatch = self.node_count != self.result.node_count
            if node_count_mismatch:
                patch = dict(op='replace', value=self.node_count, path='/node_count')
                patch_list.append(patch)

            # There appears to be a patch needed to apply
            if len(patch_list) > 0:
                self.magnum_client.clusters.update(self.result.uuid, patch_list)
                raise WaitCondition("Applying patch to the cluster: {}".format(patch_list))

        # Since the cluster exists but the requested state is absent, delete the cluster
        elif self.state == 'absent':
            self.magnum_client.clusters.delete(self.result.uuid)
            raise WaitCondition("Deleting cluster: {}".format(self.result.uuid))
        
if __name__ == '__main__':
    module = AnsibleModule(
        argument_spec = dict(
            cloud_name=dict(required=True, type='str'),
            state=dict(default='present', choices=['present','absent']),
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
    changed = container_infra.get()
    result_dict = container_infra.result_dict

    module.exit_json(changed=changed, container_infra=result_dict)
