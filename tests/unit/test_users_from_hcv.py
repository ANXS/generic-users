"""Contract and HTTP-level tests for users_from_hcv."""

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import hvac
import hvac.exceptions


class FakeKVV2:
    def __init__(self, lists, reads):
        self.lists = lists
        self.reads = reads

    def list_secrets(self, path):
        if path not in self.lists:
            raise hvac.exceptions.InvalidPath("missing")
        return {"data": {"keys": self.lists[path]}}

    def read_secret_version(self, path, **_kwargs):
        if path not in self.reads:
            raise hvac.exceptions.InvalidPath("missing")
        data, deletion_time = self.reads[path]
        return {
            "data": {
                "data": data,
                "metadata": {"deletion_time": deletion_time},
            }
        }


class FakeClient:
    def __init__(self, lists, reads):
        self.secrets = type("Secrets", (), {})()
        self.secrets.kv = type("KV", (), {})()
        self.secrets.kv.v2 = FakeKVV2(lists, reads)


def test_load_users_from_vault_covers_key_lifecycle(hcv_module):
    lists = {
        "yopo/users": [
            "inactive/",
            "deleted-user/",
            "active/",
            "ignored-value",
        ],
        "yopo/users/active/authorized_keys": [
            "without-comment",
            "with-comment",
        ],
        "yopo/users/active/authorized_keys_removed": ["retired", "deleted"],
        "yopo/users/inactive/authorized_keys": [],
        "yopo/users/inactive/authorized_keys_removed": ["must-not-emit"],
    }
    reads = {
        "yopo/users/active/meta": (
            {
                "contexts": ["test"],
                "groups": "staff, operators",
                "comment": "Active",
                "password": "locked",
                "ssh_keys_exclusive": True,
                "api_token": "token",
            },
            "",
        ),
        "yopo/users/inactive/meta": (
            {"contexts": ["other"], "groups": ["staff"]},
            "",
        ),
        "yopo/users/deleted-user/meta": (
            {"contexts": ["test"], "groups": ["staff"]},
            "2026-09-19T00:00:00Z",
        ),
        "yopo/users/inactive/authorized_keys_removed/must-not-emit": (
            {"type": "ssh-ed25519", "key": "INACTIVE"},
            "",
        ),
        "yopo/users/active/authorized_keys/with-comment": (
            {"type": "ssh-ed25519", "key": "ACTIVE1", "comment": "first"},
            "",
        ),
        "yopo/users/active/authorized_keys/without-comment": (
            {"type": "ssh-ed25519", "key": "ACTIVE2"},
            "",
        ),
        "yopo/users/active/authorized_keys_removed/retired": (
            {"type": "ssh-ed25519", "key": "RETIRED", "comment": "old"},
            "",
        ),
        "yopo/users/active/authorized_keys_removed/deleted": (
            {"type": "ssh-ed25519", "key": "DELETED"},
            "2026-09-19T00:00:00Z",
        ),
    }

    facts = hcv_module.load_users_from_vault(
        FakeClient(lists, reads),
        "yopo/users",
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
            "ssh_keys": [
                "ssh-ed25519 ACTIVE1 first",
                "ssh-ed25519 ACTIVE2",
            ],
            "comment": "Active",
            "pass": "locked",
            "ssh_keys_exclusive": True,
            "api_token": "token",
        }
    ]
    assert [user["name"] for user in facts["genericusers_users_removed"]] == [
        "inactive"
    ]
    assert facts["genericusers_keys_removed"] == [
        {
            "user": "active",
            "key": "ssh-ed25519 RETIRED old",
        }
    ]


def test_missing_optional_key_collections_are_empty(hcv_module):
    client = FakeClient(
        {"yopo/users": ["active/"]},
        {
            "yopo/users/active/meta": (
                {"contexts": "all", "groups": []},
                "",
            )
        },
    )
    facts = hcv_module.load_users_from_vault(client, "yopo/users")
    assert facts["genericusers_users"][0]["ssh_keys"] == []
    assert facts["genericusers_keys_removed"] == []


class VaultFixtureHandler(BaseHTTPRequestHandler):
    seen_tokens = []

    def log_message(self, _format, *_args):
        return

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_LIST(self):
        self.seen_tokens.append(self.headers.get("X-Vault-Token"))
        path = urlparse(self.path).path
        listings = {
            "/v1/secret/metadata/yopo/users": ["alice/"],
            "/v1/secret/metadata/yopo/users/alice/authorized_keys": ["main"],
            "/v1/secret/metadata/yopo/users/alice/authorized_keys_removed": [
                "old"
            ],
        }
        if path not in listings:
            self.send_json(404, {"errors": []})
            return
        self.send_json(200, {"data": {"keys": listings[path]}})

    def do_GET(self):
        self.seen_tokens.append(self.headers.get("X-Vault-Token"))
        path = urlparse(self.path).path
        records = {
            "/v1/secret/data/yopo/users/alice/meta": {
                "contexts": ["test"],
                "groups": "staff",
            },
            "/v1/secret/data/yopo/users/alice/authorized_keys/main": {
                "type": "ssh-ed25519",
                "key": "ACTIVE",
            },
            "/v1/secret/data/yopo/users/alice/authorized_keys_removed/old": {
                "type": "ssh-ed25519",
                "key": "OLD",
            },
        }
        if path not in records:
            self.send_json(404, {"errors": []})
            return
        self.send_json(
            200,
            {
                "data": {
                    "data": records[path],
                    "metadata": {"deletion_time": ""},
                }
            },
        )


@contextmanager
def vault_fixture():
    VaultFixtureHandler.seen_tokens = []
    server = HTTPServer(("127.0.0.1", 0), VaultFixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_port
    finally:
        server.shutdown()
        thread.join()


def test_real_hvac_client_against_local_vault_protocol_fixture(hcv_module):
    with vault_fixture() as address:
        client = hvac.Client(url=address, token="fixture-token")
        facts = hcv_module.load_users_from_vault(
            client,
            "yopo/users",
            contexts="test",
        )

    assert facts["genericusers_users"][0]["ssh_keys"] == [
        "ssh-ed25519 ACTIVE"
    ]
    assert facts["genericusers_keys_removed"] == [
        {"user": "alice", "key": "ssh-ed25519 OLD"}
    ]
    assert VaultFixtureHandler.seen_tokens
    assert set(VaultFixtureHandler.seen_tokens) == {"fixture-token"}


def test_context_normalization_and_key_rendering(hcv_module):
    assert hcv_module.normalize_list("staff, operators, ") == [
        "staff",
        "operators",
    ]
    assert hcv_module.valid_context(
        ["production"], {"contexts": "test, production"}
    )
    assert hcv_module.key_string(
        {"type": "ssh-ed25519", "key": "KEY", "comment": "named"}
    ) == "ssh-ed25519 KEY named"
    assert hcv_module.key_string(
        {"type": "ssh-ed25519", "key": "KEY"}
    ) == "ssh-ed25519 KEY"


def test_main_sanitizes_vault_failures(monkeypatch, hcv_module):
    class ModuleFailure(Exception):
        pass

    class FakeModule:
        params = {
            "contexts": "",
            "extra_fields": "",
            "users_path": "yopo/users",
            "vault_addr": "http://vault.invalid",
            "vault_token": "super-secret-token",
        }

        def fail_json(self, **kwargs):
            raise ModuleFailure(kwargs["msg"])

        def exit_json(self, **_kwargs):
            raise AssertionError("main unexpectedly succeeded")

    def failing_client(**_kwargs):
        raise hvac.exceptions.Forbidden(
            "request contained super-secret-token and secret body"
        )

    monkeypatch.setattr(
        hcv_module, "AnsibleModule", lambda **_kwargs: FakeModule()
    )
    monkeypatch.setattr(hcv_module.hvac, "Client", failing_client)

    try:
        hcv_module.main()
    except ModuleFailure as error:
        message = str(error)
        assert message == "Vault request failed: Forbidden"
        assert "super-secret-token" not in message
        assert "secret body" not in message
    else:
        raise AssertionError("Vault failure did not reach fail_json")
