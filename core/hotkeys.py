"""Validated single-key emergency toggle shortcuts (polling, no global hook)."""

HOTKEY_CHOICES = tuple(f'F{number}' for number in range(6, 13))
DEFAULT_HOTKEY = 'F9'


def normalize_hotkey(value):
    value = str(value).strip().upper()
    return value if value in HOTKEY_CHOICES else DEFAULT_HOTKEY


def hotkey_vk(value):
    """Windows VK_F1=0x70; unsupported settings fail safely to F9."""
    return 0x70 + int(normalize_hotkey(value)[1:]) - 1
