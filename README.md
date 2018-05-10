OpenStack Container Clusters
============================

This role can be used to register container cluster templates in Magnum
using the Magnum CLI.

Requirements
------------

The OpenStack Magnum API should be accessible from the target host.

Role Variables
--------------

`os_container_infra_config.endpoint` is the endpoint for Magnum API.

`os_container_infra_config.name` is the name to call the cluster.

`os_container_infra_config.template` is the cluster template to use for the cluster.

`os_container_infra_config.keypair` is the keypair to use to access the cluster nodes.

`os_container_infra_config.master_count` is the number of master nodes.

`os_container_infra_config.node_count` is the number of worker nodes.

`os_container_infra_config.interfaces` is a list of additional network interfaces to
attach to the cluster since Magnum only allows attachment of one network
interface by default.

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
          my_container_infra_config: |
            ---
            cloud_name: mycloud
            magnum_endpoint: http://openstack.example.com:9511/v1
            cluster_name: test-cluster
            cluster_template_name: swarm-fedora-atomic-27
            keypair: default
            master_count: 1
            node_count: 1
            interfaces:
             - p3-lln
             - p3-bdn
      ...
      roles:
      - { role: stackhpc.os-config,
          os_config_content: "{{ my_cloud_config }}" }
      - { role: stackhpc.os-container-infra,
          os_container_infra_config: "{{ my_container_infra_config | from_yaml }}"}

License
-------

Apache 2

Author Information
------------------

- Bharat Kunwar (<bharat@stackhpc.com>)
