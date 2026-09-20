# ANXS.generic-users

[![Molecule CI](https://github.com/ANXS/generic-users/actions/workflows/ci.yml/badge.svg)](https://github.com/ANXS/generic-users/actions/workflows/ci.yml)

Manage local groups, users, passwords, supplementary groups, and authorized SSH
keys. User data can be supplied directly, loaded from a directory tree, or
loaded from HashiCorp Vault KV v2 by the included controller-side modules.

## Supported platforms

The CI matrix covers:

- Debian 12 (Bookworm)
- Debian 13 (Trixie)
- Ubuntu 20.04 (Focal)
- Ubuntu 22.04 (Jammy)
- Ubuntu 24.04 (Noble)

The role requires Ansible 2.12 or newer. The loader modules execute on the
controller and require PyYAML; Vault-backed loading also requires `hvac`.

## Role variables

```yaml
genericusers_groups:
  - name: dbadmins
    gid: 5000
    system: false

genericusers_groups_removed:
  - name: defunctadmins

# Additive by default. Individual users can override this value.
genericusers_ssh_keys_exclusive: false

genericusers_users:
  - name: foo
    group: dbadmins
    groups:
      - staff
      - devops
    append: false
    pass: "$6$..."
    comment: Foo account
    shell: /bin/bash
    home: /home/foo
    ssh_keys:
      - "ssh-ed25519 AAAA... foo@example"
    ssh_keys_exclusive: true

genericusers_users_removed:
  - name: baz

# Explicit tombstones are removals, even when exclusive mode is disabled.
genericusers_keys_removed:
  - user: foo
    key: "ssh-ed25519 AAAA... retired-key"
```

An omitted key is not a removal. In additive mode, unrelated keys remain in
`authorized_keys`. In exclusive mode, the declared list is the exact desired
set; an empty exclusive list removes every key. Explicit tombstones run after
key installation, so a key present in both lists is removed.

## Static user loader

`library/users_from_yaml.py` reads one leaf directory per user:

```text
users/
└── foo/
    ├── meta.yml
    ├── password
    ├── authorized_keys
    ├── authorized_keys_removed
    └── optional-extra-field
```

`meta.yml` may contain `contexts`, `groups`, `comment`, and
`ssh_keys_exclusive`. Authorized-key files contain one public key per line;
blank lines are ignored.

```yaml
- name: Load users from files
  users_from_yaml:
    users_dir: /path/to/users
    contexts: web,production
    extra_fields: web_password:web_pass,api_token
  delegate_to: localhost
  become: false
```

The module emits `genericusers_users`, `genericusers_users_removed`, and
`genericusers_keys_removed` under `ansible_facts`.

## Vault user loader

`library/users_from_hcv.py` reads Vault KV v2 data under
`<users_path>/<username>`:

```text
yopo/users/foo/meta
yopo/users/foo/authorized_keys/<key-name>
yopo/users/foo/authorized_keys_removed/<key-name>
```

Key records contain `type`, `key`, and an optional `comment`. The metadata
record accepts the same user fields as the static loader. Set `VAULT_ADDR`
and `VAULT_TOKEN` in the controller environment; do not place the token in
inventory or task output.

```yaml
- name: Load users from Vault
  users_from_hcv:
    users_path: yopo/users
    contexts: web,production
  delegate_to: localhost
  become: false
  no_log: true
```

## Development

Create the local virtual environment and run lint plus module contracts:

```console
make lint unit
```

Run one platform or the complete matrix:

```console
make test-ubuntu2404
make test
```

`make test` runs production-profile Ansible linting, YAML linting, Python
module contract tests, Molecule convergence, idempotence, and Testinfra across
all five supported operating systems. `make act-lint` and `make act-test`
run the corresponding GitHub Actions jobs locally when `act` is installed.

## License

MIT. See [LICENSE](LICENSE).
