from pbc_chaos.web.runner import metadata_payload


def test_metadata_payload_detects_gemini_key_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=dotenv-key\n", encoding="utf-8")

    payload = metadata_payload()

    assert payload["geminiConfigured"] is True
