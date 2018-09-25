OpenStack Container Clusters
============================

This role can be used to manipulate container cluster in Magnum using the
Magnum python client.

Requirements
------------

- python 2.6+
- openstacksdk
- python-magnumclient
- python-heatclient
- python-novaclient

Role Variables
--------------

`os_container_infra_cloud` is the name of the cloud inside cloud.yaml.

`os_container_infra_user` is the name of the SSH user, e.g. fedora.

`os_container_infra_state` must be either present or absent.

`os_container_infra_cluster_name` is the name of the cluster.

`os_container_infra_cluster_template_name` is the cluster template to use for
the cluster.

`os_container_infra_keypair` is the keypair to use to access the cluster nodes.

`os_container_infra_master_count` is the number of master nodes.

`os_container_infra_node_count` is the number of worker nodes.

`os_container_infra_external_interface` is the interface on which a cluster can
be accessed externally.

`os_container_infra_interfaces` is a list of additional network interfaces to.

`os_container_infra_inventory` is the destination where the inventory will be saved to.
attach to the servers in a cluster since Magnum only allows attachment of one
network interface by default.

Example Playbook
----------------

The following playbook creates a cluster, attaches two interfaces to servers in
the cluster and creates an inventory file using authentication information
available in the environment variables (which is the default behaviour):

    ---
    - hosts: localhost
      become: False
      gather_facts: False
      roles:
      - role: stackhpc.os-container-infra
        os_container_infra_auth_type: environment # default behaviour
        # container specific variables
        os_container_infra_user: fedora
        os_container_infra_state: present
        os_container_infra_cluster_name: test-cluster
        os_container_infra_cluster_template_name: swarm-fedora-atomic-27
        os_container_infra_keypair: default
        os_container_infra_master_count: 1
        os_container_infra_node_count: 1
        os_container_infra_external_interface: p3-internal
        os_container_infra_interfaces:
        - p3-lln
        - p3-bdn
    ...

To authenticate using information passed via playbook:

    ---
    - hosts: localhost
      become: False
      gather_facts: False
      roles:
      - role: stackhpc.os-container-infra
        os_container_infra_auth_type: password
        os_container_infra_auth:
          auth_url: http://10.60.253.1:5000
          project_name: p3
          username: username
          password: password
          user_domain_name: Default
          project_domain_name: Default
          region_name: RegionOne
        # ...container specific variables
    ...

To authenticate using the information stored in `.config/openstack/clouds.yaml`
which can be generated using our `stackhpc.os-config` role:

    ---
    - hosts: localhost
      become: False
      gather_facts: False
      roles:
      - role: stackhpc.os-config
        os_config_content: |
          ---
          clouds:
            mycloud:
              auth:
                auth_url: http://10.60.253.1:5000
                project_name: p3
                username: username
                password: password
                user_domain_name: Default
                project_domain_name: Default
              region: RegionOne
          ...
      - role: stackhpc.os-container-infra
        os_container_infra_auth_type: cloud
        os_container_infra_cloud: mycloud
        # ...container specific variables
    ...

Ansible Debug Info
------------------

To view warnings emitted by this role, export the following
following variable before running ansible:

    export ANSIBLE_LOG_PATH=ansible.log
    export ANSIBLE_DEBUG=1

To filter these warnings:

    tail -f ansible.log | grep DEBUG

License
-------

Apache 2

Author Information
------------------

- Bharat Kunwar (<bharat@stackhpc.com>)
