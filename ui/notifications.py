"""
Centralised notification helpers.
All show_toast / show_confirm calls go through here so message copy,
icons, and durations are defined in one place.
"""

from PyQt6.QtCore import QTimer
from ui.icons import Icons, get_mdi_font


def _icon_html(icon) -> str:
    family = get_mdi_font().family()
    return f'<span style="font-family: \'{family}\'; font-size: 16px;">{icon}</span>'


def _with_icon(icon, message: str) -> str:
    return f"{_icon_html(icon)}&nbsp;&nbsp;{message}"


# ── Entity ───────────────────────────────────────────────────────────────────

def notify_entity_unavailable(dashboard, label: str):
    """Shown when the user taps a button whose entity is unavailable/unknown."""
    dashboard.show_toast(_with_icon(Icons.ALERT_CIRCLE_OUTLINE, f"{label} is unavailable"))


# ── Glass UI ─────────────────────────────────────────────────────────────────

def notify_glass_ui_warning(dashboard):
    """Shown once when Glass UI is first enabled."""
    msg = _with_icon(
        Icons.ALERT_CIRCLE_OUTLINE,
        "Glass UI is experimental \u2014 not optimised for light mode and may impact "
        "performance on low-end hardware.",
    )
    QTimer.singleShot(600, lambda: dashboard.show_toast(msg, duration_ms=8000))


# ── Button / grid ─────────────────────────────────────────────────────────────

def notify_page_full(dashboard, page_num: int):
    """Shown when a button cannot be moved because the target page is full."""
    dashboard.show_toast(f"Page {page_num} is full. Cannot move button.")


def notify_move_as_1x1(dashboard, orig_w: int, orig_h: int, page_num: int, on_confirm):
    """Confirm dialog asking if a button should be moved as 1×1 instead."""
    dashboard.show_confirm(
        f"No room at {orig_w}\u00d7{orig_h} on Page {page_num}. Move as 1\u00d71?",
        on_confirm=on_confirm,
    )


# ── Updates ───────────────────────────────────────────────────────────────────

def notify_update_available(dashboard, new_version: str, on_confirm):
    """Confirm dialog offering to open the releases page for a new version."""
    dashboard.show_confirm(
        f"Prism Desktop {new_version} is available. Download now?",
        on_confirm=on_confirm,
    )


# ── Connection / settings ─────────────────────────────────────────────────────

def notify_missing_credentials(dashboard):
    """Shown when Test Connection is pressed with empty URL or token."""
    dashboard.show_toast(
        _with_icon(Icons.LAN_DISCONNECT, "Missing URL or token \u2014 fill in both fields first.")
    )


def notify_connection_test_result(dashboard, success: bool, message: str):
    """Shown after a connection test completes."""
    icon = Icons.LAN_CONNECT if success else Icons.LAN_DISCONNECT
    dashboard.show_toast(_with_icon(icon, message))


def notify_geoclue2_missing(dashboard, install_cmd: str):
    """Shown on Linux when GeoClue2 is not installed."""
    dashboard.show_toast(f"GeoClue2 not found. Install: {install_cmd}")
