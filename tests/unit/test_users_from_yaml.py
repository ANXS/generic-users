"""Contract tests for users_from_yaml."""


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_users_emits_active_removed_and_tombstone_facts(
    tmp_path, yaml_module
):
    active = tmp_path / "active"
    write(
        active / "meta.yml",
        """
contexts:
  - test
groups: "staff, operators"
comment: Active User
ssh_keys_exclusive: true
""".strip(),
    )
    write(active / "password", "locked")
    write(active / "api_token", "token-value")
    write(
        active / "authorized_keys",
        "ssh-ed25519 ACTIVE active\n\n",
    )
    write(
        active / "authorized_keys_removed",
        "ssh-ed25519 RETIRED retired\n\n",
    )

    inactive = tmp_path / "inactive"
    write(inactive / "meta.yml", "contexts: [other]\n")
    write(
        inactive / "authorized_keys_removed",
        "ssh-ed25519 MUST_NOT_EMIT inactive\n",
    )

    facts = yaml_module.load_users(
        str(tmp_path),
        contexts="test",
        extra_fields="api_token",
    )

    assert facts["genericusers_users"] == [
        {
            "name": "active",
            "home": "/home/active",
            "append": True,
            "shell": "/bin/bash",
            "groups": ["staff", "operators"],
            "ssh_keys": ["ssh-ed25519 ACTIVE active"],
            "comment": "Active User",
            "ssh_keys_exclusive": True,
            "pass": "locked",
            "api_token": "token-value",
        }
    ]
    assert [user["name"] for user in facts["genericusers_users_removed"]] == [
        "inactive"
    ]
    assert facts["genericusers_keys_removed"] == [
        {
            "user": "active",
            "key": "ssh-ed25519 RETIRED retired",
        }
    ]


def test_all_context_is_always_active(tmp_path, yaml_module):
    write(tmp_path / "global" / "meta.yml", "contexts: all\n")
    facts = yaml_module.load_users(str(tmp_path))
    assert [user["name"] for user in facts["genericusers_users"]] == ["global"]


def test_missing_directory_fails(yaml_module):
    try:
        yaml_module.load_users("/definitely/not/a/user/tree")
    except FileNotFoundError as error:
        assert "not found" in str(error)
    else:
        raise AssertionError("missing users_dir did not fail")


def test_non_mapping_metadata_fails(tmp_path, yaml_module):
    write(tmp_path / "bad" / "meta.yml", "- not\n- a\n- mapping\n")
    try:
        yaml_module.load_users(str(tmp_path))
    except ValueError as error:
        assert "YAML mapping" in str(error)
    else:
        raise AssertionError("non-mapping metadata did not fail")


def test_extra_field_mapping(yaml_module):
    assert yaml_module.parse_extra_fields(
        "web_password:web_pass,api_key"
    ) == [
        ("web_password", "web_pass"),
        ("api_key", "api_key"),
    ]


def test_context_and_list_normalization(yaml_module):
    assert yaml_module.normalize_list("staff, operators, ") == [
        "staff",
        "operators",
    ]
    assert yaml_module.valid_context(
        ["production"], {"contexts": "test, production"}
    )
    assert yaml_module.valid_context([], {"contexts": ["all"]})
    assert not yaml_module.valid_context(
        ["production"], {"contexts": ["test"]}
    )


def test_empty_users_directory_emits_empty_facts(tmp_path, yaml_module):
    facts = yaml_module.load_users(str(tmp_path))
    assert facts == {
        "genericusers_users": [],
        "genericusers_users_removed": [],
        "genericusers_keys_removed": [],
    }


def test_empty_files_and_directory_order_are_deterministic(
    tmp_path, yaml_module
):
    write(tmp_path / "zeta" / "meta.yml", "contexts: all\n")
    write(tmp_path / "zeta" / "password", "")
    write(tmp_path / "zeta" / "authorized_keys", "\n\n")
    write(tmp_path / "alpha" / "meta.yml", "contexts: all\n")

    facts = yaml_module.load_users(str(tmp_path))

    assert [user["name"] for user in facts["genericusers_users"]] == [
        "alpha",
        "zeta",
    ]
    zeta = facts["genericusers_users"][1]
    assert zeta["pass"] == ""
    assert zeta["ssh_keys"] == []


def test_malformed_yaml_fails(tmp_path, yaml_module):
    write(tmp_path / "bad" / "meta.yml", "contexts: [unterminated\n")
    try:
        yaml_module.load_users(str(tmp_path))
    except yaml_module.yaml.YAMLError:
        pass
    else:
        raise AssertionError("malformed metadata did not fail")
