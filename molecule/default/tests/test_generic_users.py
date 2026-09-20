"""Behavioral tests for ANXS.generic-users."""


def authorized_keys(host, username):
    """Return the user's authorized_keys content, or an empty string."""
    key_file = host.file("/home/%s/.ssh/authorized_keys" % username)
    return key_file.content_string if key_file.exists else ""


def test_created_groups(host):
    explicit = host.group("genericusers_created")
    automatic = host.group("genericusers_default_gid")
    assert explicit.exists
    assert explicit.gid == 22000
    assert automatic.exists
    assert automatic.gid != explicit.gid


def test_default_user_attributes(host):
    user = host.user("gu_default")
    assert user.exists
    assert user.uid == 22001
    assert user.group == "genericusers_test"
    assert user.home == "/home/gu_default"
    assert user.shell == "/bin/bash"
    assert user.gecos == "Generic Users default"
    assert "genericusers_created" in user.groups
    assert "genericusers_prior" not in user.groups


def test_default_mode_is_additive(host):
    content = authorized_keys(host, "gu_default")
    assert "desired-one" in content
    assert "unmanaged" in content


def test_role_wide_exclusive_mode_is_exact(host):
    content = authorized_keys(host, "gu_global")
    assert "desired-one" in content
    assert "desired-two" in content
    assert "unmanaged" not in content
    assert len([line for line in content.splitlines() if line]) == 2


def test_per_user_false_overrides_role_exclusive(host):
    content = authorized_keys(host, "gu_override_additive")
    assert "desired-one" in content
    assert "unmanaged" in content


def test_per_user_true_is_exact(host):
    content = authorized_keys(host, "gu_override_exclusive")
    assert "desired-one" in content
    assert "desired-two" in content
    assert "unmanaged" not in content


def test_empty_exclusive_set_removes_every_key(host):
    assert authorized_keys(host, "gu_empty") == ""


def test_explicit_tombstone_wins_without_exclusive_mode(host):
    content = authorized_keys(host, "gu_tombstone")
    assert "retired" not in content
    assert "unmanaged" in content


def test_active_and_tombstoned_key_is_absent(host):
    content = authorized_keys(host, "gu_conflict")
    assert "desired-one" not in content
    assert "unmanaged" in content
    assert "retired" in content


def test_fact_based_input_reaches_role(host):
    content = authorized_keys(host, "gu_fact")
    assert "desired-two" in content
    assert "unmanaged" not in content


def test_removed_user_and_home_are_absent(host):
    assert not host.user("gu_remove").exists
    assert not host.file("/home/gu_remove").exists


def test_removed_group_is_absent(host):
    assert not host.group("genericusers_remove").exists
