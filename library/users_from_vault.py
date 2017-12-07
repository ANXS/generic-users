#!/usr/bin/env python

import os
import hvac

def main():
    mod = AnsibleModule(
        argument_spec=dict(
            contexts=dict(default=''),
            vault_token=dict(no_log=True),
            vault_server=dict(),
            vault_path=dict(rquired=True)
        )
    )
    with_contexts = []
    if 'contexts' in mod.params:
        with_contexts = mod.params['contexts'].split(',')

    vault_server = None
    if 'vault_server' in mod.params:
        vault_server = mod.params['vault_server']
    else:
        vault_server = os.environ['VAULT_ADDR']

    vault_path = mod.params['vault_path']
    client = hvac.Client(vault_server)

    if 'vault_token' in mod.params:
        client.token = mod.params['vault_token']

    all_users = client.list(vault_path)
