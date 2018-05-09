OpenStack Container Clusters
============================

This role can be used to register container cluster templates in magnum
using the magnum CLI.

Requirements
------------

The OpenStack magnum API should be accessible from the target host.

Role Variables
--------------

`os_container_infra.name` is the name to call the cluster.

`os_container_infra.template` is the cluster template to use for the cluster.

`os_container_infra.keypair` is the keypair to use to access the cluster nodes.

`os_container_infra.master_count` is the number of master nodes.

`os_container_infra.worker_count` is the number of worker nodes.

`os_container_infra.interfaces` is a list of additional network interfaces to
attach to the cluster since magnum only allows attachment of one network
interface by default.

Dependencies
------------

This role depends on the `stackhpc.os-shade` role.

Example Playbook
----------------

The following playbook registers a cluster template.

    ---
    - hosts: all
      vars:
        my_cloud_config: |
          ---
          clouds:
            mycloud:
              auth:
                auth_url: http://openstack.example.com:5000
                project_name: p3
                username: user
                password: secretpassword
              region: RegionOne
      roles:
        - { role: stackhpc.os-config,
            os_config_content: "{{ my_cloud_config }}" }
        - role: stackhpc.os-container-infra
          os_container_infra_config:
            - name: swarm-cluster
              template: swarm-fedora-atomic-27
              interfaces:
               - p3-lln
               - p3-bdn

Author Information
------------------

- Bharat Kunwar (<bharat@stackhpc.com>)
