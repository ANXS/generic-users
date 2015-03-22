## ANXS - generic-users [![Build Status](https://travis-ci.org/ANXS/generic-users.png)](https://travis-ci.org/ANXS/generic-users)

Ansible role which manages the groups and user accounts.


#### Requirements & Dependencies
- Tested on Ansible 1.9 or higher.


#### Variables

The *hosts: []* is used as a more fine grained, second filter for choosing which hosts the groups and users are created on.
Obviously, a group might be present on some/all hosts and be without any members (users) while a user that is
configured to be part of a group, expects that group to be present on the respective host. See the example below for more clarifications:

```yaml
genericusers_groups:
  - name: "admin"
    hosts: ["databases"] # On which host group(s) you want the group to be created. Default is "all".
    gid: 5000            # (Optional)
    system: no           # (Optional)
  - name: "staff"
    hosts: ["all"]
    gid: 6000
    system: no

genericusers_groups_removed:
  - name: "old_admin"
    hosts: ["all"]        # From which host group(s) you want the group to be removed. Default is "all".

genericusers_users:
  - name: "foo"
    groups: ["admin", "staff"] # The group(s) listed here need to exist on the hosts beforehand.
    ssh_keys:                  # Keys to add to authorized_keys. Store them in the files directory.
      - "ssh-rsa aaa"
      - "ssh-rsa bbb"
    hosts: ["databases"]       # On which host group(s) you want the user to be created. Default is "all".
    append: "no"               # (Optional) If yes, will only add groups, not set them to just the list in groups.
    pass: "$6$...."            # (Optional) Set the user's password to this crypted value.
    comment: "foo acc"         # (Optional) 
    shell: "/bin/bash"         # (Optional) Set the user's shell.
    home: "/home/baz"          # (Optional) Set the user's home directory.
    system: no                 # (Optional) Make the user a system account or not.
  - name: "bar"
    groups: ["staff"]
    ssh_keys: []
    hosts: ["all"]

genericusers_users_removed:
  - name: baz
    hosts: ["all"]      # From which hosts you want the user to be removed. Default is "all".
```


#### License

Licensed under the MIT License. See the LICENSE file for details.


#### Feedback, bug-reports, requests, ...

Are [welcome](https://github.com/ANXS/generic-users/issues)!
