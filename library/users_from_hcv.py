#!/usr/bin/env python
import os
import yaml
import hvac
import hvac.exceptions

def keys_from_vault(client, vault_path, user):
    actual_path = "%s/%s/authorized_keys" % (vault_path, user)
    vault_resp = client.secrets.kv.v2.list_secrets(actual_path)
    if not vault_resp:
        raise Exception('unexpected vault response')

    return vault_resp['data']['keys']

def key_from_vault(client, vault_path, user, key):
    actual_path = "%s/%s/authorized_keys/%s" % (vault_path, user, key)
    try:
        vault_resp = client.secrets.kv.v2.read_secret_version(actual_path)
        if vault_resp['data']['metadata']['deletion_time'] != '':
            return None

        return vault_resp['data']['data']
    except hvac.exceptions.InvalidPath:
        return None

def user_from_vault(client, vault_path, user):
    actual_path = "%s/%s/meta" % (vault_path, user)
    try:
        vault_resp = client.secrets.kv.v2.read_secret_version(actual_path)
        if vault_resp['data']['metadata']['deletion_time'] != '':
            return None

        return vault_resp['data']['data']
    except hvac.exceptions.InvalidPath:
        return None

def users_from_vault(client, vault_path):
    vault_resp = client.secrets.kv.v2.list_secrets(vault_path)
    if not vault_resp:
        raise Exception('unexpected vault response')

    return [x[:-1] for x in vault_resp['data']['keys'] if x[-1] == '/']

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
            users_path=dict(),
            vault_addr=dict()
        )
    )

    with_contexts = []
    if 'contexts' in mod.params:
        with_contexts = mod.params['contexts'].split(',')

    if not 'users_path' in mod.params:
        return problems(mod, "Must specify users_path")

    add_users = []
    remove_users = []

    client = hvac.Client(url=mod.params['vault_addr'])
    users = users_from_vault(client, mod.params['users_path'])

    for username in users:
        vault_obj = user_from_vault(client, mod.params['users_path'], username)
        user_obj = {
            'name': username,
            'home': "/home/%s" % username,
            'append': True,
            'shell': '/bin/bash',
            'groups': vault_obj.get('groups', []).split(','),
            'ssh_keys': []
        }
        if 'comment' in vault_obj.keys() and vault_obj['comment']:
            user_obj['comment'] = vault_obj['comment']

        if 'password' in vault_obj.keys():
            user_obj['pass'] = vault_obj['password']

        user_keys = keys_from_vault(client, mod.params['users_path'], username)
        ssh_keys = []
        for user_key in user_keys:
            key_obj = key_from_vault(client, mod.params['users_path'], username, user_key)
            if key_obj:
                ssh_keys.append("%s %s %s" % (key_obj['type'], key_obj['key'], key_obj['comment']))

        if len(ssh_keys) > 0:
            user_obj['ssh_keys'] = ssh_keys

        if valid_context(with_contexts, vault_obj):
            add_users.append(user_obj)
        else:
            remove_users.append(user_obj)

    facts = {
        'genericusers_users': add_users,
        'genericusers_users_removed': remove_users
    }
    mod.exit_json(changed=False, ansible_facts=facts)

# magic pyramids from the stars
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
main()
