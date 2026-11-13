"""Application-wide configuration for Inventory Intelligence."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "Inventory Intelligence"
APP_TAGLINE = "Stock & Material Planning"
APP_VERSION = "1.0.0"
PAGE_ICON = "📦"

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATE_FILE = TEMPLATES_DIR / "inventory-intelligence-template.xlsx"
DEMO_FILE = TEMPLATES_DIR / "inventory-intelligence-demo.xlsx"

MAX_UPLOAD_SIZE_MB = 10
ALLOWED_EXTENSIONS = ("xlsx",)

DEMO_SOURCE = "demo"
UPLOAD_SOURCE = "upload"
