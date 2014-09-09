## ANXS - generic-users [![Build Status](https://travis-ci.org/ANXS/generic-users.png)](https://travis-ci.org/ANXS/generic-users)

Ansible role which manages the groups and user accounts.


#### Requirements & Dependencies
- Tested on Ansible 1.4 or higher.


#### Variables

```yaml
genericusers_groups:
  - name: "dbadmins"
    gid: 5000
    system: no
  - name: "mailadmins"
    gid: 6000
    system: no

genericusers_groups_removed:
  - name: "defunctadmins"

genericusers_users:
  - name: "foo"
    groups: ["admin", "staff", "devops"]
    ssh_keys:
      - "ssh-dss ......."
      - "ssh-dss ......."
    append: "no"        # If yes, will only add groups, not set them to just the list in groups.
    pass: "$6$...."     # Set the user's password to this crypted value.
    comment: "foo acc"  # 
    shell: "/bin/bash"  # Set the user's shell.
    home: "/home/baz"   # Set the user's home directory.
    system: no          # Make the user a system account or not.
  - name: "bar"
    groups: ["admin", "staff", "dev"]
    ssh_keys: []

genericusers_users_removed:
  - name: baz
```


#### License

Licensed under the MIT License. See the LICENSE file for details.


#### Feedback, bug-reports, requests, ...

Are [welcome](https://github.com/ANXS/generic-users/issues)!
