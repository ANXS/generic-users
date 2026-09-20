#!/usr/bin/python
"""Load generic-users facts from HashiCorp Vault KV v2."""

import os

import hvac
import hvac.exceptions
from ansible.module_utils.basic import AnsibleModule


def normalize_list(value):
    """Normalize a comma-separated string or sequence to a clean list."""
    if not value:
        return []
    if isinstance(value, str):
        value = value.split(",")
    return [str(item).strip() for item in value if str(item).strip()]


def valid_context(with_contexts, metadata):
    """Return whether a user belongs to one of the requested contexts."""
    requested = normalize_list(with_contexts)
    user_contexts = normalize_list(metadata.get("contexts", []))
    return "all" in user_contexts or bool(set(requested) & set(user_contexts))


def parse_extra_fields(raw):
    """Parse comma-separated source[:destination] extra-field mappings."""
    result = []
    for entry in normalize_list(raw):
        if ":" in entry:
            source, destination = entry.split(":", 1)
            result.append((source.strip(), destination.strip()))
        else:
            result.append((entry, entry))
    return result


def _key_names_from_vault(client, vault_path, user, key_collection):
    actual_path = "%s/%s/%s" % (vault_path, user, key_collection)
    try:
        response = client.secrets.kv.v2.list_secrets(actual_path)
    except hvac.exceptions.InvalidPath:
        return []
    return sorted(response["data"]["keys"])


def keys_from_vault(client, vault_path, user):
    return _key_names_from_vault(client, vault_path, user, "authorized_keys")


def removed_keys_from_vault(client, vault_path, user):
    return _key_names_from_vault(
        client, vault_path, user, "authorized_keys_removed"
    )


def key_from_vault(
    client, vault_path, user, key, key_collection="authorized_keys"
):
    actual_path = "%s/%s/%s/%s" % (
        vault_path,
        user,
        key_collection,
        key,
    )
    try:
        response = client.secrets.kv.v2.read_secret_version(
            actual_path, raise_on_deleted_version=True
        )
    except hvac.exceptions.InvalidPath:
        return None
    if response["data"]["metadata"]["deletion_time"]:
        return None
    return response["data"]["data"]


def user_from_vault(client, vault_path, user):
    actual_path = "%s/%s/meta" % (vault_path, user)
    try:
        response = client.secrets.kv.v2.read_secret_version(
            actual_path, raise_on_deleted_version=True
        )
    except hvac.exceptions.InvalidPath:
        return None
    if response["data"]["metadata"]["deletion_time"]:
        return None
    return response["data"]["data"]


def users_from_vault(client, vault_path):
    response = client.secrets.kv.v2.list_secrets(vault_path)
    return sorted(
        key[:-1] for key in response["data"]["keys"] if key.endswith("/")
    )


def key_string(key_object):
    """Render one Vault key object as an authorized_keys line."""
    parts = [key_object["type"], key_object["key"]]
    if key_object.get("comment"):
        parts.append(key_object["comment"])
    return " ".join(parts)


def load_users_from_vault(client, vault_path, contexts="", extra_fields=""):
    """Build generic-users facts from Vault KV v2."""
    add_users = []
    remove_users = []
    remove_keys = []
    field_mappings = parse_extra_fields(extra_fields)

    for username in users_from_vault(client, vault_path):
        vault_object = user_from_vault(client, vault_path, username)
        if vault_object is None:
            continue

        user_object = {
            "name": username,
            "home": "/home/%s" % username,
            "append": True,
            "shell": "/bin/bash",
            "groups": normalize_list(vault_object.get("groups", [])),
            "ssh_keys": [],
        }

        for field, destination in (
            ("comment", "comment"),
            ("password", "pass"),
            ("ssh_keys_exclusive", "ssh_keys_exclusive"),
        ):
            if field in vault_object and vault_object[field] not in (None, ""):
                user_object[destination] = vault_object[field]

        for source, destination in field_mappings:
            if source in vault_object:
                user_object[destination] = vault_object[source]

        for key_name in keys_from_vault(client, vault_path, username):
            key_object = key_from_vault(
                client, vault_path, username, key_name
            )
            if key_object:
                user_object["ssh_keys"].append(key_string(key_object))

        if valid_context(contexts, vault_object):
            add_users.append(user_object)
            for key_name in removed_keys_from_vault(
                client, vault_path, username
            ):
                key_object = key_from_vault(
                    client,
                    vault_path,
                    username,
                    key_name,
                    key_collection="authorized_keys_removed",
                )
                if key_object:
                    remove_keys.append(
                        {
                            "user": username,
                            "key": key_string(key_object),
                        }
                    )
        else:
            remove_users.append(user_object)

    return {
        "genericusers_users": add_users,
        "genericusers_users_removed": remove_users,
        "genericusers_keys_removed": remove_keys,
    }


def main():
    """Ansible module entry point."""
    module = AnsibleModule(
        argument_spec={
            "contexts": {"type": "str", "default": ""},
            "extra_fields": {"type": "str", "default": ""},
            "users_path": {"type": "str", "required": True},
            "vault_addr": {"type": "str"},
            "vault_token": {"type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    client_options = {}
    vault_addr = module.params["vault_addr"] or os.environ.get("VAULT_ADDR")
    vault_token = module.params["vault_token"] or os.environ.get("VAULT_TOKEN")
    if vault_addr:
        client_options["url"] = vault_addr
    if vault_token:
        client_options["token"] = vault_token

    try:
        client = hvac.Client(**client_options)
        facts = load_users_from_vault(
            client,
            module.params["users_path"],
            module.params["contexts"],
            module.params["extra_fields"],
        )
    except hvac.exceptions.VaultError as error:
        module.fail_json(
            msg="Vault request failed: %s" % error.__class__.__name__
        )
    except ValueError as error:
        module.fail_json(msg="Invalid Vault user data: %s" % error)

    module.exit_json(changed=False, ansible_facts=facts)


if __name__ == "__main__":
    main()
