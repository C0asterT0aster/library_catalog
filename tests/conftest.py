"""Pytest configuration and fixtures."""
import sys
from unittest.mock import MagicMock

# Mock Home Assistant modules before any imports
homeassistant_mock = MagicMock()
sys.modules["homeassistant"] = homeassistant_mock
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules["homeassistant.helpers.typing"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.webhook"] = MagicMock()

# Add parent directory to path so we can import custom_components
sys.path.insert(0, str(__file__).rsplit("\\", 1)[0] + "/..")
