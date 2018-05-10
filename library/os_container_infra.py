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
from magnumclient.client import Client
from magnumclient.exceptions import *
import openstack
import time

display = Display()

def get_os_cloud(cloud_name, module):
    os_cloud = openstack.connect(cloud=cloud_name)
    os_cloud.authorize()
    return os_cloud

def get_update_or_create_container_infra(magnum_client, module, **kwargs):
    try:
        # Get cluster details
        container_infra_details = magnum_client.clusters.get(kwargs['name'])
        if container_infra_details.status.endswith('FAILED'):
            # If the cluster is in a failed status, raise error:
            module.fail_json(
                msg="Cluster is not usable because: {}.".format(container_infra_details.faults))
        elif container_infra_details.status.endswith('PROGRESS'):
            # If the cluster creation and update is in progress:
            display.warning(container_infra_details.status)
            return False
        elif container_infra_details.status.endswith('COMPLETE'):
            # If the cluster looks ready
            # Raise error if there is a mismatch between cluster template ids
            cluster_template_mismatch = kwargs['cluster_template_id'] != container_infra_details.cluster_template_id 
            if cluster_template_mismatch:
                module.fail_json(
                    msg="Cluster template mismatch for an existing cluster.")

            patch_list = list()

            # Update number of masters if there is a mismatch
            master_count_mismatch = kwargs['master_count'] != container_infra_details.master_count
            if master_count_mismatch:
                patch = dict(op='replace',
                     value=kwargs['master_count'],
                     path='/master_count')
                patch_list.append(patch)

            # Update number of nodes if there is a mismatch
            node_count_mismatch = kwargs['node_count'] != container_infra_details.node_count
            if node_count_mismatch:
                patch = dict(op='replace',
                     value=kwargs['node_count'],
                     path='/node_count')
                patch_list.append(patch)

            if patch_list:
                # There appears to be a patch needed to apply
                magnum_client.clusters.update(container_infra_details.uuid, patch_list)
                display.warning("Applying patch to the cluster: {}".format(patch_list))
                return False
            else:
                # Everything looks okay, return cluster details
                return container_infra_details
        else:
            module.fail_json(
                msg="Cluster returned unexpected status: {}".format(container_infra_details.status))
    except NotFound:
        # Create new cluster here if no cluster with the name was found
        magnum_client.clusters.create(**kwargs)
        display.warning("Cluster called {} does not exist, creating new.".format(kwargs['name']))
        return False

def main():
    module = AnsibleModule(
        argument_spec = dict(
            cloud_name=dict(required=True, type='str'),
            magnum_endpoint=dict(required=True, type='str'),
            cluster_name=dict(required=True, type='str'),
            cluster_template_name=dict(required=True, type='str'),
            master_count=dict(required=True, type='int'),
            node_count=dict(required=True, type='int'),
            keypair=dict(required=True, type='str'),
        ),
        supports_check_mode=False
    )

    cloud_name = module.params['cloud_name']
    magnum_endpoint = module.params['magnum_endpoint']
    os_cloud = get_os_cloud(cloud_name,  module)
    magnum_client = Client('1', endpoint_override=magnum_endpoint, session=os_cloud.session)

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
    while True:
        container_infra_details = get_update_or_create_container_infra(magnum_client, module, **kwargs)
        display.warning(container_infra_details)
        if container_infra_details:
            stack_id = container_infra_details.stack_id
            display.warning(stack_id)
            module.exit_json(changed=False, details=stack_id)
        else:
            # Wait until this is not False
            if fail_after < tries:
                module.fail_json(
                    msg="Failing after {} tries.".format(fail_after))
            else:
                display.warning('Tries: [{}/{}]'.format(tries, fail_after))
                time.sleep(10)
                tries += 1

if __name__ == '__main__':
    main()
