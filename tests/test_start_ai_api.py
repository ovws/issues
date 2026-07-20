from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_batch_locates_project_and_preserves_exit_code():
    content = (ROOT / "start-ai-api.bat").read_text(encoding="utf-8")

    assert "%~dp0" in content
    assert "scripts\\start-ai-api.ps1" in content
    assert "set \"EXIT_CODE=%ERRORLEVEL%\"" in content
    assert "exit /b %EXIT_CODE%" in content


def test_batch_supports_noninteractive_execution():
    content = (ROOT / "start-ai-api.bat").read_text(encoding="utf-8")

    assert "if not defined AI_API_NO_PAUSE pause" in content


def test_powershell_covers_all_services_and_isolation_rules():
    content = (ROOT / "scripts" / "start-ai-api.ps1").read_text(encoding="utf-8-sig")

    for name, port in (
        ("grok", "8001"),
        ("gemini", "8002"),
        ("chatgpt-image", "8003"),
        ("admin", "8090"),
    ):
        assert f"Key = '{name}'" in content
        assert f"Port = {port}" in content

    assert "start-service.ps1" in content
    assert "start-admin.ps1" in content
    assert "Test-DirectoryWritable" in content
    assert "Test-FileWritable" in content
    assert "data\\chatgpt-image.db" in content
    assert "repair-runtime-permissions.ps1" in content
    assert "docker" not in content.lower()
    assert "compose" not in content.lower()
    assert "continue" in content
    assert "exit 1" in content
    assert "exit 0" in content


def test_runtime_root_can_resolve_the_primary_worktree():
    content = (ROOT / "scripts" / "start-ai-api.ps1").read_text(encoding="utf-8-sig")

    assert "[string]$RuntimeRoot" in content
    assert "AI_API_RUNTIME_ROOT" in content
    assert "--git-common-dir" in content
    assert "运行目录" in content


def test_health_probe_uses_models_only_as_fallback():
    content = (ROOT / "scripts" / "start-ai-api.ps1").read_text(encoding="utf-8-sig")

    assert "@('/health', '/v1/models')" in content
    assert "AI_API_GROK_HEALTH_KEY" in content
    assert "AI_API_GEMINI_HEALTH_KEY" in content
    assert "AI_API_CHATGPT_IMAGE_HEALTH_KEY" in content


def test_scripts_do_not_embed_secret_values():
    batch = (ROOT / "start-ai-api.bat").read_text(encoding="utf-8")
    powershell = (ROOT / "scripts" / "start-ai-api.ps1").read_text(encoding="utf-8-sig")
    combined = batch + powershell

    assert "sk-internal-" not in combined
    assert "__Secure-1PSID=" not in combined
    assert "CHATGPT2API_AUTH_KEY=" not in combined
    assert "GROK_UPSTREAM_API_KEY=" not in combined


def test_permission_repair_is_scoped_and_preserves_databases():
    content = (ROOT / "scripts" / "repair-runtime-permissions.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "#Requires -RunAsAdministrator" in content
    assert "RuntimeRoot cannot be a drive root" in content
    assert "Relative = 'data'" in content
    assert "Relative = 'logs'" in content
    assert "Relative = 'run'" in content
    assert "upstream\\grok2api\\data" in content
    assert "upstream\\chatgpt2api\\data" in content
    assert "Remove-Item" not in content
    assert "Delete" not in content
