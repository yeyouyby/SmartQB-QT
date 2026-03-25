import os
import pytest
from .config_manager import ConfigManager

@pytest.fixture
def config_manager(tmp_path):
    db_file = tmp_path / "test_config.db"
    cm = ConfigManager(str(db_file))
    # Load safe environment secret or default
    master_key = os.environ.get("TEST_MASTER_PASSWORD", "safe_test_master_123")
    cm.set_master_key(master_key)
    return cm

def test_plain_value_roundtrip(config_manager):
    config_manager.set_value("theme", "dark", encrypt=False)
    assert config_manager.get_value("theme") == "dark"

def test_encrypted_value_roundtrip(config_manager):
    test_key = os.environ.get("TEST_OPENAI_API_KEY", "placeholder-openai-key")
    config_manager.set_value("openai_api_key", test_key, encrypt=True)
    assert config_manager.get_value("openai_api_key") == test_key

def test_missing_key_default(config_manager):
    assert config_manager.get_value("nonexistent", "fallback") == "fallback"
