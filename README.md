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

`os_container_infra_cloud` is the name of the cloud ( configured inside cloud.yaml, optional).

`os_container_infra_user` is the name of the SSH user, e.g. fedora.

`os_container_infra_state` must be either present, absent, query or upgrade.

`os_container_infra_cluster_name` is the name of the cluster.

`os_container_infra_cluster_template_name` is the cluster template to use for
the cluster.

`os_container_infra_keypair` is the keypair to use to access the cluster nodes.

`os_container_infra_master_count` is the number of master nodes.

`os_container_infra_node_count` is the number of worker nodes.

`os_container_infra_default_interface` is the default network to use to reach the cluster.

`os_container_infra_interfaces` is a list of additional networks to attach to cluster nodes.

`os_container_infra_inventory` is the destination where the inventory will be saved to.
attach to the servers in a cluster since Magnum only allows attachment of one
network interface by default.

`os_container_infra_environment_group` is an optional Ansible group name to
which all cluster hosts and localhost will be added. This can be useful if
there is a single group that represents an environment such as
development/staging/production.

`os_container_infra_coe` is container orchestration engine to use. Valid
options are `kubernetes` or `swarm`.

`os_container_infra_k8s_version` is a configurable Kubernetes version to use when
`os_container_infra_state = upgrade`.

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
        os_container_infra_user: fedora
        os_container_infra_state: present
        os_container_infra_cluster_name: k8s
        os_container_infra_cluster_template_name: k8s-fa29
        os_container_infra_roles:
        - name: storage_client
          groups: ["{{ os_container_infra_worker_group }}"]
        os_container_infra_keypair: bharat
        os_container_infra_default_interface: default
        os_container_infra_master_group:
          - name: master
            count: 1
        os_container_infra_worker_group:
          - name: minion
            count: 2
    ...

To authenticate using information passed via playbook, supply a dictionary variable as given:

        os_container_infra_auth:
          auth_url: http://10.60.253.1:5000
          project_name: p3
          username: username
          password: password
          user_domain_name: Default
          project_domain_name: Default
          region_name: RegionOne

To authenticate using the information stored inside
`.config/openstack/clouds.yaml` or `/etc/openstack/clouds.yaml` which can be
generated using our `stackhpc.os-config` role, append the following:

        os_container_infra_auth_type: cloud
        os_container_infra_cloud: mycloud

For upgrades of Kubernetes cluster:

        ---
        - hosts: cluster
          gather_facts: False
          become: yes
          roles:
          - role: stackhpc.os-container-infra
            os_container_infra_state: upgrade
            os_container_infra_k8s_version: v1.13.4
            os_container_infra_coe: kubernetes
        ...

Ansible Debug Info
------------------

To view warnings emitted by this role, export the following
following variable before running ansible:

    export ANSIBLE_LOG_PATH=ansible.log
    export ANSIBLE_DEBUG=1

To filter these warnings:

    tail -f ansible.log | grep DEBUG

Known Issues
------------

The `template` Ansible modules writes an inventory file and it may complain
about missing `libselinux-python` which is already installed is most Linux
distros. If thats the case, simply create a symlink to the selinux directory in
your existing virtual environment:

    ln -s /usr/lib64/python2.7/site-packages/selinux/ venv/lib64/python2.7/site-packages/

For a new virtual environment:

    virtualenv --system-site-packages venv

License
-------

Apache 2

Author Information
------------------

- Bharat Kunwar (<bharat@stackhpc.com>)
