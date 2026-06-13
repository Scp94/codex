import importlib


def test_settings_read_host_roots_from_environment(monkeypatch):
    monkeypatch.setenv("MONITOR_PROC_ROOT", "/custom/proc")
    monkeypatch.setenv("MONITOR_SYS_ROOT", "/custom/sys")
    monkeypatch.setenv("MONITOR_DISK_PATHS", "/data,/var")
    monkeypatch.setenv("MONITOR_API_TOKEN", "secret")

    config = importlib.import_module("monitor_platform.config")
    reloaded = importlib.reload(config)

    assert reloaded.settings.proc_root == "/custom/proc"
    assert reloaded.settings.sys_root == "/custom/sys"
    assert reloaded.settings.disk_paths == ("/data", "/var")
    assert reloaded.settings.api_token == "secret"

