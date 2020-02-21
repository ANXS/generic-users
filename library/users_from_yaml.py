#!/usr/bin/env python
import os, yaml

def problems(mod, msg):
    """Ansible module exist with an error."""
    return mod.exit_json(changed=False, failed=True, msg=msg)

def valid_context(with_contexts, meta):
    """Determines if the user is in context."""
    context = False
    if len(with_contexts) > 0 and 'contexts' in meta:
        if 'all' in meta['contexts']:
            context = True
        else:
            for ctx in meta['contexts']:
                if not context:
                    if ctx in with_contexts:
                        context = True
    elif 'contexts' in meta and 'all' in meta['contexts']:
        context = True

    return context

def main():
    mod = AnsibleModule(
        argument_spec=dict(
            contexts=dict(default=''),
            users_dir=dict()
        )
    )

    with_contexts = []
    if 'contexts' in mod.params:
        with_contexts = mod.params['contexts'].split(',')

    users_dir = None
    if 'users_dir' in mod.params:
        users_dir = mod.params['users_dir'].rstrip('/')
    else:
        return problems(mod, "Must specify users_dir")

    if not os.path.isdir(users_dir):
        return problems(mod, ("%s not found" % users_dir))

    users = []
    remove_users = []

    # lets look for users
    for dirname, subdir, files in os.walk(users_dir):
        # if we have subdirectories then we are not a user directory
        if len(subdir) > 0:
            continue
        username = os.path.basename(dirname)
        user = {
            'name': username,
            'home': "/home/%s" % username,
            'append': True,
            'shell': '/bin/bash',
            'groups': [],
            'authorized_keys': []
        }
        context = False
        # groups and gecos from metadata yamls
        if 'meta.yml' in files:
            meta_h = open("%s/meta.yml" % dirname, 'r')
            meta = yaml.load(meta_h)
            meta_h.close()
            # if contexts exist, then check validity
            context = valid_context(with_contexts, meta)

            if 'comment' in meta:
                user['comment'] = meta['comment']
            if 'groups' in meta:
                user['groups'] = meta['groups']
            if 'github_user' in meta:
                user['github_user'] = meta['github_user']

        # read password if exists
        if 'password' in files:
            pw_h = open("%s/password" % dirname, 'r')
            user['pass'] = pw_h.read().strip()
            pw_h.close()
        if 'authorized_keys' in files:
            key_h = open("%s/authorized_keys" % dirname, 'r')
            user['ssh_keys'] = key_h.read().split('\n')
            key_h.close()
        else:
            user['ssh_keys'] = []

        if context:
            users.append(user)
        else:
            remove_users.append(user)

    facts = {
        'genericusers_users': users,
        'genericusers_users_removed': remove_users
    }
    mod.exit_json(changed=False, ansible_facts=facts)

# magic pyramids from the stars
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
main()
