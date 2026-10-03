"""Resolve the independent Windows app and taskbar appearance preferences."""


def windows_theme(value_name):
    try:
        import winreg
        path = r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            light, _ = winreg.QueryValueEx(key, value_name)
        return 'light' if int(light) else 'dark'
    except (OSError, ValueError, TypeError, ImportError):
        return 'dark'


def interface_theme(preference='system'):
    """Explicit app setting wins; system mode follows Windows app appearance."""
    if preference in ('dark', 'light'):
        return preference
    return windows_theme('AppsUseLightTheme')


def system_tray_theme():
    """Explorer taskbar can have a different theme than applications."""
    return windows_theme('SystemUsesLightTheme')
