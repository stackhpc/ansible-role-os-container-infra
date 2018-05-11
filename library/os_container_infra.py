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
from magnumclient.client import Client as MagnumClient
from magnumclient.exceptions import *
from heatclient.client import Client as HeatClient
import openstack
import time
import json

display = Display()

class WaitCondition(Exception):
    def __init__(self, message, errors):

        # Call the base class constructor with the parameters it needs
        super(WaitCondition, self).__init__(message)

        # Now for your custom code...
        self.errors = errors

def get_os_cloud(cloud_name):
    os_cloud = openstack.connect(cloud=cloud_name)
    os_cloud.authorize()
    return os_cloud

def get_container_infra(magnum_client, create_if_not_found=True, **kwargs):
    try:
        return magnum_client.clusters.get(kwargs['name'])
    except NotFound as e:
        # Create new cluster here if no cluster with the name was found
        if create_if_not_found:
            magnum_client.clusters.create(**kwargs)
            raise WaitCondition("Cluster called {} does not exist, creating new.".format(kwargs['name']))
        else:
            raise e

def update_container_infra(magnum_client, container_infra, **kwargs):
    # Raise module error if there is a mismatch between cluster template ids
    cluster_template_mismatch = kwargs['cluster_template_id'] != container_infra.cluster_template_id 
    if cluster_template_mismatch:
        module.fail_json(
            msg="Cluster template mismatch for an existing cluster.")

    # Patch list to append list of patches
    patch_list = list()

    # Update number of masters if there is a mismatch
    master_count_mismatch = kwargs['master_count'] != container_infra.master_count
    if master_count_mismatch:
        patch = dict(op='replace',
             value=kwargs['master_count'],
             path='/master_count')
        patch_list.append(patch)

    # Update number of nodes if there is a mismatch
    node_count_mismatch = kwargs['node_count'] != container_infra.node_count
    if node_count_mismatch:
        patch = dict(op='replace',
             value=kwargs['node_count'],
             path='/node_count')
        patch_list.append(patch)

    if len(patch_list) > 0:
        # There appears to be a patch needed to apply
        magnum_client.clusters.update(container_infra.uuid, patch_list)
        raise WaitCondition("Applying patch to the cluster: {}".format(patch_list))
        
def main():
    module = AnsibleModule(
        argument_spec = dict(
            cloud_name=dict(required=True, type='str'),
            create_if_not_found=dict(required=True, type='bool'),
            cluster_name=dict(required=True, type='str'),
            cluster_template_name=dict(required=True, type='str'),
            master_count=dict(required=True, type='int'),
            node_count=dict(required=True, type='int'),
            keypair=dict(required=True, type='str'),
        ),
        supports_check_mode=False
    )

    os_cloud = get_os_cloud(module.params['cloud_name'])
    magnum_client = MagnumClient('1', endpoint_override=False, session=os_cloud.session)

    cluster_template_name = module.params['cluster_template_name']
    cluster_template_id = magnum_client.cluster_templates.get(cluster_template_name).uuid

    kwargs = dict(name=module.params['cluster_name'],
                    cluster_template_id=cluster_template_id,
                    master_count=module.params['master_count'],
                    node_count=module.params['node_count'],
                    keypair=module.params['keypair'],
                )

    tries = 0
    fail_after = 100
    changed = False
    container_infra = False
    while container_infra == False:
        try:
            # Get cluster info or raise WaitCondition if a new one is created.
            container_infra = get_container_infra(magnum_client, module.params['create_if_not_found'], **kwargs)
            if container_infra.status.endswith('FAILED'):
                # If the cluster is in a failed status, raise error:
                module.fail_json(
                    msg="Cluster is not usable because: {}.".format(container_infra.faults))
            elif container_infra.status.endswith('PROGRESS'):
                # If the cluster creation and update is in progress:
                raise WaitCondition(container_infra.status)
            elif container_infra.status.endswith('COMPLETE'):
                # Since the cluster looks ready, raise a WaitCondition if cluster is updated.
                update_container_infra(magnum_client, container_infra, **kwargs)
            else:
                module.fail_json(
                    msg="Cluster returned unexpected status: {}".format(container_infra.status))
        except WaitCondition as e:
            if fail_after < tries:
                # This is taking far too long, terminate.
                module.fail_json(
                    msg="Failing after {} tries.".format(fail_after))
            else:
                # Wait before trying again.
                display.debug('[DEBUG] Tries: [{}/{}] {}'.format(tries, fail_after, e))
                time.sleep(10)
                tries += 1
                changed = True
                container_infra = False

    stack_id = container_infra.stack_id
    display.debug('[DEBUG] Value of stack_id: {}'.format(stack_id))

    stack_resources = get_stack_resources(stack_id)

    heat_client = HeatClient('1', session=os_cloud.session)
    resources = heat_client.resources.list(stack_id,nested_depth=4)

    module.exit_json(changed=changed, container_infra=container_infra.to_dict())

if __name__ == '__main__':
    main()
