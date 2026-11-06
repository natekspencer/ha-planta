"""Tests for the Planta integration."""

try:
    from pytest_homeassistant.common import MockConfigEntry
except ImportError:  # Home Assistant < 2026.11
    from pytest_homeassistant_custom_component.common import MockConfigEntry

__all__ = ["MockConfigEntry"]
