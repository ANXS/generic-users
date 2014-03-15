## Ansibles - generic_users [![Build Status](https://travis-ci.org/Ansibles/generic_users.png)](https://travis-ci.org/Ansibles/generic_users)

Ansible role which manages the groups and user accounts.


#### Requirements & Dependencies
- Tested on Ansible 1.4 or higher.


#### Variables

```yaml
genericusers_groups:
  - name: "dbadmins"
  - name: "mailadmins"

genericusers_groups_removed:
  - name: "defunctadmins"

genericusers_users:
  - name: "foo"
    groups: ["admin", "staff", "devops"]
    ssh_keys:
      - "ssh-dss ......."
      - "ssh-dss ......."
    append: "no"        # (optional) If yes, will only add groups, not set them to just the list in groups.
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


#### License

Licensed under the MIT License. See the LICENSE file for details.


#### Feedback, bug-reports, requests, ...

Are [welcome](https://github.com/ansibles/generic_users/issues)!
