import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
import unittest

spec = importlib.util.spec_from_file_location(
    "duck_installer", Path(__file__).resolve().parents[1] / "install.py"
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.config = self.root / "config"
        self.state = self.root / "state"
        self.source.mkdir()
        self.config.mkdir()
        self.state.mkdir()
        (self.source / "manifest.json").write_text(
            json.dumps(
                {"version": "1.0.0", "entryPoints": {"service": "src/Service.qml"}}
            )
        )
        (self.source / "src").mkdir()
        (self.source / "src/Service.qml").write_text("new")
        (self.source / "src/DuckModel.js").write_text("model")
        (self.source / "src/assets").mkdir()
        (self.source / "src/assets/quack.wav").write_bytes(b"audio")
        (self.source / "review").mkdir()
        (self.source / "review/private.json").write_text("not runtime")
        (self.source / "tests").mkdir()
        (self.source / "tests/test.cjs").write_text("not runtime")
        self.target = self.config / "plugins" / installer.PLUGIN_ID
        self.target.mkdir(parents=True)
        (self.target / "Service.qml").write_text("previous")
        self.settings = {
            "bar": {
                "layout": {
                    "right": [
                        {"id": installer.PLUGIN_ID, "palette": "mallard"},
                        {"id": "other", "color": "old"},
                    ]
                }
            }
        }
        (self.config / "shell.json").write_text(json.dumps(self.settings))
        (self.state / "memory.json").write_text('{"trust":77,"fed":12}')
        self.calls = []
        self.status_calls = 0
        self.fail = None
        self.old_service = False
        self.locked = False

    def run_command(self, command, **kwargs):
        self.calls.append(command)
        if command == ["omarchy-shell", "lock", "isLocked"]:
            return types.SimpleNamespace(
                returncode=0, stdout="true" if self.locked else "false"
            )
        if command[:3] == ["omarchy-shell", "desktop-duck", "status"]:
            self.status_calls += 1
            return types.SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "version": "0.0.0"
                        if self.status_calls == 1 or self.old_service
                        else "1.0.0",
                        "runState": "active",
                        "paused": self.status_calls == 1,
                        "opened": False,
                    }
                ),
            )
        if command[:4] == ["omarchy", "plugin", "list", "--json"]:
            return types.SimpleNamespace(
                returncode=0, stdout=json.dumps([{"id": installer.PLUGIN_ID}])
            )
        if command[:3] == ["omarchy", "plugin", "enable"]:
            current = json.loads((self.config / "shell.json").read_text())
            current["bar"]["layout"]["right"][0]["palette"] = "white"
            current["bar"]["layout"]["right"][1]["color"] = "user-edited"
            (self.config / "shell.json").write_text(json.dumps(current))
        if self.fail and self.fail(command):
            self.fail = None
            raise subprocess.CalledProcessError(1, command)
        return types.SimpleNamespace(returncode=0, stdout="")

    def install(self, **kwargs):
        return installer.install(
            self.source,
            self.config,
            self.state,
            run=self.run_command,
            sleep=lambda _: None,
            **kwargs,
        )

    def test_success_packages_only_runtime_and_keeps_backup(self):
        target, backup = self.install()
        service = (
            target
            / json.loads((target / "manifest.json").read_text())["entryPoints"][
                "service"
            ]
        )
        self.assertEqual(service.read_text(), "new")
        self.assertFalse((target / "review").exists())
        self.assertFalse((target / "tests").exists())
        self.assertEqual((service.parent / "assets/quack.wav").read_bytes(), b"audio")
        self.assertEqual((backup / "plugin/Service.qml").read_text(), "previous")
        self.assertEqual(json.loads((backup / "memory.json").read_text())["fed"], 12)
        self.assertIn(["omarchy-shell", "desktop-duck", "action", "pause"], self.calls)

    def test_preflight_validation_excludes_development_symlinks(self):
        (self.source / ".venv/bin").mkdir(parents=True)
        (self.source / ".venv/bin/python").symlink_to("/usr/bin/python")
        validated = []

        def run(command, **kwargs):
            if command[:3] == ["omarchy", "plugin", "validate"]:
                path = Path(command[3])
                validated.append(path)
                self.assertNotEqual(path, self.source)
                self.assertFalse((path / ".venv").exists())
                manifest = json.loads((path / "manifest.json").read_text())
                self.assertTrue((path / manifest["entryPoints"]["service"]).is_file())
            return self.run_command(command, **kwargs)

        installer.install(
            self.source, self.config, self.state, run=run, sleep=lambda _: None
        )
        self.assertEqual(len(validated), 2)

    def test_first_install_without_settings_memory_or_existing_plugin(self):
        shutil.rmtree(self.target)
        shutil.rmtree(self.state)
        (self.config / "shell.json").unlink()

        def run(command, **kwargs):
            if command == ["omarchy-shell", "desktop-duck", "status"]:
                self.calls.append(command)
                self.status_calls += 1
                return types.SimpleNamespace(
                    returncode=1 if self.status_calls == 1 else 0,
                    stdout=""
                    if self.status_calls == 1
                    else json.dumps(
                        {"version": "1.0.0", "runState": "active", "paused": False}
                    ),
                )
            if command[:3] == ["omarchy", "plugin", "enable"]:
                self.calls.append(command)
                (self.config / "shell.json").write_text(
                    json.dumps(
                        {"bar": {"layout": {"right": [{"id": installer.PLUGIN_ID}]}}}
                    )
                )
                return types.SimpleNamespace(returncode=0, stdout="")
            return self.run_command(command, **kwargs)

        target, backup = installer.install(
            self.source, self.config, self.state, run=run, sleep=lambda _: None
        )
        manifest = json.loads((target / "manifest.json").read_text())
        self.assertTrue((target / manifest["entryPoints"]["service"]).is_file())
        self.assertFalse((backup / "plugin").exists())
        self.assertFalse((backup / "memory.json").exists())
        self.assertNotIn(["omarchy-shell", "desktop-duck", "save"], self.calls)
        self.assertIn(["omarchy", "plugin", "enable", installer.PLUGIN_ID], self.calls)

    def test_snapshot_install_never_replaces_git_history(self):
        (self.target / ".git").mkdir()
        with self.assertRaisesRegex(RuntimeError, "managed by git"):
            self.install()
        self.assertTrue((self.target / ".git").is_dir())
        self.assertEqual((self.target / "Service.qml").read_text(), "previous")
        self.assertFalse((self.state / "backups").exists())

    def test_enable_failure_restores_plugin_and_only_our_settings(self):
        self.fail = lambda command: command[:3] == ["omarchy", "plugin", "enable"]
        with self.assertRaises(subprocess.CalledProcessError):
            self.install()
        self.assertEqual((self.target / "Service.qml").read_text(), "previous")
        entries = json.loads((self.config / "shell.json").read_text())["bar"]["layout"][
            "right"
        ]
        self.assertEqual(entries[0]["palette"], "mallard")
        self.assertEqual(entries[1]["color"], "user-edited")
        self.assertEqual(
            json.loads((self.state / "memory.json").read_text())["fed"], 12
        )

    def test_old_service_version_is_not_a_successful_install(self):
        self.old_service = True
        with self.assertRaisesRegex(RuntimeError, "did not start"):
            self.install()
        self.assertEqual((self.target / "Service.qml").read_text(), "previous")

    def test_invalid_json_leaves_existing_installation_alone(self):
        (self.config / "shell.json").write_text("broken")
        with self.assertRaises(json.JSONDecodeError):
            self.install()
        self.assertEqual((self.target / "Service.qml").read_text(), "previous")
        self.assertFalse((self.state / "backups").exists())

    def test_changed_code_gets_a_fresh_qml_url_without_restart(self):
        self.install()
        first = json.loads((self.target / "manifest.json").read_text())["entryPoints"][
            "service"
        ]
        (self.source / "src/DuckModel.js").write_text("changed model")
        self.install()
        second = json.loads((self.target / "manifest.json").read_text())["entryPoints"][
            "service"
        ]
        self.assertNotEqual(first, second)
        self.assertNotIn(["omarchy", "restart", "shell"], self.calls)

    def test_restart_is_refused_while_session_is_locked(self):
        self.locked = True
        with self.assertRaisesRegex(RuntimeError, "Session is locked"):
            self.install(restart=True)
        self.assertEqual((self.target / "Service.qml").read_text(), "previous")


if __name__ == "__main__":
    unittest.main()
