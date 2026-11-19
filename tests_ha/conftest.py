"""Integration tests inside a real (test) Home Assistant, via pytest-homeassistant-custom-component."""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    yield
