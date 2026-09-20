#!/usr/bin/python
"""Load generic-users facts from a directory tree."""

import os

import yaml
from ansible.module_utils.basic import AnsibleModule


def normalize_list(value):
    """Normalize a comma-separated string or sequence to a clean list."""
    if not value:
        return []
    if isinstance(value, str):
        value = value.split(",")
    return [str(item).strip() for item in value if str(item).strip()]


def valid_context(with_contexts, meta):
    """Return whether a user belongs to one of the requested contexts."""
    requested = normalize_list(with_contexts)
    user_contexts = normalize_list(meta.get("contexts", []))
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


def read_text(path):
    """Read a UTF-8 text file without trailing whitespace."""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def read_lines(path):
    """Read non-empty UTF-8 lines."""
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle.read().splitlines() if line.strip()]


def read_metadata(path):
    """Read and validate one user metadata file."""
    with open(path, "r", encoding="utf-8") as handle:
        metadata = yaml.safe_load(handle) or {}
    if not isinstance(metadata, dict):
        raise ValueError("%s must contain a YAML mapping" % path)
    return metadata


def load_users(users_dir, contexts="", extra_fields=""):
    """Build generic-users facts from a directory tree."""
    if not users_dir:
        raise ValueError("users_dir is required")
    if not os.path.isdir(users_dir):
        raise FileNotFoundError("%s not found" % users_dir)

    users = []
    remove_users = []
    remove_keys = []
    field_mappings = parse_extra_fields(extra_fields)

    for dirname, subdirectories, filenames in os.walk(users_dir):
        subdirectories.sort()
        filenames.sort()
        if dirname == users_dir or subdirectories:
            continue

        username = os.path.basename(dirname)
        user = {
            "name": username,
            "home": "/home/%s" % username,
            "append": True,
            "shell": "/bin/bash",
            "groups": [],
            "ssh_keys": [],
        }

        metadata = {}
        if "meta.yml" in filenames:
            metadata = read_metadata(os.path.join(dirname, "meta.yml"))
            for field in ("comment", "ssh_keys_exclusive"):
                if field in metadata:
                    user[field] = metadata[field]
            if "groups" in metadata:
                user["groups"] = normalize_list(metadata["groups"])

        if "password" in filenames:
            user["pass"] = read_text(os.path.join(dirname, "password"))

        for source, destination in field_mappings:
            if source in filenames:
                user[destination] = read_text(os.path.join(dirname, source))

        if "authorized_keys" in filenames:
            user["ssh_keys"] = read_lines(os.path.join(dirname, "authorized_keys"))

        removed_keys = []
        if "authorized_keys_removed" in filenames:
            removed_keys = read_lines(
                os.path.join(dirname, "authorized_keys_removed")
            )

        if valid_context(contexts, metadata):
            users.append(user)
            remove_keys.extend(
                {"user": username, "key": key} for key in removed_keys
            )
        else:
            remove_users.append(user)

    return {
        "genericusers_users": users,
        "genericusers_users_removed": remove_users,
        "genericusers_keys_removed": remove_keys,
    }


def main():
    """Ansible module entry point."""
    module = AnsibleModule(
        argument_spec={
            "contexts": {"type": "str", "default": ""},
            "extra_fields": {"type": "str", "default": ""},
            "users_dir": {"type": "path", "required": True},
        },
        supports_check_mode=True,
    )

    try:
        facts = load_users(
            module.params["users_dir"],
            module.params["contexts"],
            module.params["extra_fields"],
        )
    except (OSError, ValueError, yaml.YAMLError) as error:
        module.fail_json(msg="Unable to load users from YAML: %s" % error)

    module.exit_json(changed=False, ansible_facts=facts)


if __name__ == "__main__":
    main()
