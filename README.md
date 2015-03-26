## ANXS - generic-users [![Build Status](https://travis-ci.org/ANXS/generic-users.png)](https://travis-ci.org/ANXS/generic-users)

Ansible role which manages the groups and user accounts.


#### Requirements & Dependencies
- Tested on Ansible 1.8 or higher.


#### Variables

```yaml
genericusers_groups:
  - name: "dbadmins"
    gid: 5000           # (Optional)
    system: no          # (Optional)
  - name: "mailadmins"
    gid: 6000
    system: no

genericusers_groups_removed:
  - name: "defunctadmins"

genericusers_users:
  - name: "foo"
    groups: ["admin", "staff", "devops"]
    ssh_keys:           # Keys to add to authorized_keys
      - "ssh-dss ......."
      - "ssh-dss ......."
    append: "no"        # (Optional) If yes, will only add groups, not set them to just the list in groups.
    pass: "$6$...."     # (Optional) Set the user's password to this crypted value.
    comment: "foo acc"  # (Optional)
    shell: "/bin/bash"  # (Optional) Set the user's shell.
    home: "/home/baz"   # (Optional) Set the user's home directory.
    system: no          # (Optional) Make the user a system account or not.
  - name: "bar"
    groups: ["admin", "staff", "dev"]
    ssh_keys: []

genericusers_users_removed:
  - name: baz
```


#### Testing
This project comes with a VagrantFile, this is a fast and easy way to test changes to the role, fire it up with `vagrant up`

See [vagrant docs](https://docs.vagrantup.com/v2/) for getting setup with vagrant


#### License

Licensed under the MIT License. See the LICENSE file for details.


#### Feedback, bug-reports, requests, ...

Are [welcome](https://github.com/ANXS/generic-users/issues)!
