"""Small HTML/SVG building blocks shared by the UI components."""

from __future__ import annotations

from html import escape

_ICONS: dict[str, str] = {
    "download": (
        '<path d="M12 3v12m0 0 4-4m-4 4-4-4"/>'
        '<path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>'
    ),
    "upload": (
        '<path d="M12 17V5m0 0 4 4m-4-4L8 9"/>'
        '<path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>'
    ),
    "play": '<polygon points="7 4 20 12 7 20 7 4"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "sheet": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 2v6h6"/>'
    ),
    "table": (
        '<rect x="3" y="3" width="18" height="18" rx="2"/>'
        '<path d="M3 9h18M9 21V9"/>'
    ),
    "box": (
        '<path d="m21 8-9-5-9 5 9 5 9-5z"/>'
        '<path d="M3 8v8l9 5 9-5V8"/>'
        '<path d="M12 13v8"/>'
    ),
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "alert": (
        '<path d="M12 9v4m0 4h.01"/>'
        '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
        '<path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/>'
        '<path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>'
    ),
    "sparkle": (
        '<path d="m12 3 1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z"/>'
    ),
    "arrow-right": '<path d="M5 12h14m0 0-6-6m6 6-6 6"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    "file": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 2v6h6M8 13h8M8 17h5"/>'
    ),
    "layers": (
        '<path d="m12 2 9 5-9 5-9-5 9-5z"/>'
        '<path d="m3 12 9 5 9-5M3 17l9 5 9-5"/>'
    ),
    "refresh": (
        '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/>'
        '<path d="M21 3v5h-5"/>'
    ),
    "trash": (
        '<path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/>'
        '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
        '<path d="M10 11v6M14 11v6"/>'
    ),
    "query_stats": (
        '<path d="M3 3v18h18"/>'
        '<path d="m7 15 4-5 3 3 4-6"/>'
    ),
    "inventory_2": (
        '<path d="M4 7h16v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z"/>'
        '<path d="M4 7V4a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v3"/>'
        '<path d="M10 11h4"/>'
    ),
    "shield_check": (
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<path d="m9 11.5 2 2 4-4"/>'
    ),
}


def icon(name: str, size: int = 18, class_name: str = "") -> str:
    """Return a minimal inline SVG icon."""

    body = _ICONS.get(name, _ICONS["box"])
    classes = f' class="{class_name}"' if class_name else ""
    return (
        f'<svg{classes} xmlns="http://www.w3.org/2000/svg" width="{size}" '
        f'height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{body}</svg>'
    )


def section_header(eyebrow: str, title: str, subtitle: str = "") -> str:
    """Render a consistent section heading."""

    subtitle_html = (
        f'<p class="ii-section-sub">{escape(subtitle)}</p>' if subtitle else ""
    )
    return (
        '<div class="ii-section-head">'
        "<div>"
        f'<div class="ii-section-eyebrow">{escape(eyebrow)}</div>'
        f'<h2 class="ii-section-title">{escape(title)}</h2>'
        f"{subtitle_html}"
        "</div>"
        "</div>"
    )


def banner(kind: str, title: str, message: str) -> str:
    """Render a success, warning, error or info banner."""

    icon_name = {
        "success": "check",
        "warning": "alert",
        "error": "alert",
        "info": "info",
    }.get(kind, "alert")
    return (
        f'<div class="ii-banner {escape(kind)}">'
        f'<div class="ii-banner-icon">{icon(icon_name, 18)}</div>'
        "<div>"
        f'<div class="ii-banner-title">{escape(title)}</div>'
        f'<div class="ii-banner-text">{escape(message)}</div>'
        "</div>"
        "</div>"
    )
