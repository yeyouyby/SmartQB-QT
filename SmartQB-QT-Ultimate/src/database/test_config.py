import os
from .config_manager import ConfigManager

def test_config():
    cm = ConfigManager("test_config.db")
    cm.set_master_key("my_secure_password_123")

    # Store plain setting
    cm.set_value("theme", "dark", encrypt=False)

    # Store encrypted setting
    cm.set_value("openai_api_key", os.environ.get("TEST_OPENAI_API_KEY", "sk-dummy-test-key"), encrypt=True)

    print("Theme:", cm.get_value("theme"))
    print("API Key:", cm.get_value("openai_api_key"))

if __name__ == "__main__":
    test_config()
