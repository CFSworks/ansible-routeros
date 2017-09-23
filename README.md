Ansible Modules for Mikrotik RouterOS
=====================================

Overview
--------

This repository includes the following Ansible modules:
* `ros_facts`: Return `ansible_facts` for the device
* `ros_copy`: Copy files from the local machine to the device
* `ros_fetch`: Copy files from the device to the local machine
* `ros_command`: Run a RouterOS command against the API directly
* `ros_item`: Create/update/delete configuration items in the API hierarchy

Requirements
------------

* Latest Ansible
* Latest [librouteros](https://pypi.python.org/pypi/librouteros)
* Mikrotik RouterOS-based device (e.g. RouterBOARD or Mikrotik CHR)
* API server enabled (check for port 8728 open)

Acknowledgements
----------------

I previously started by trying to update zahodi and senorsmile's
[ansible-mikrotik](https://github.com/zahodi/ansible-mikrotik) repository.

While trying to reorganize it, I decided it was ultimately better to start with
a collection of modules based more fundamentally on RouterOS's print/set/add
command set, and focus on flexibility rather than having a module for each
feature.

License
-------

Code here is released under GPLv3 for maximum compatibility with Ansible Core.
