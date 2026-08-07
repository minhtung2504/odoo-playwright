"""odoo-playwright - Tools to interact with Odoo UI using Playwright."""

from odoo_playwright.page import OdooPage
from odoo_playwright.testcase import OdooTestCase
from odoo_playwright.ui import OdooUI
from odoo_playwright.views import FormView, KanbanView, ListView

__version__ = "1.0.0"
__all__ = [
    "OdooUI",
    "OdooTestCase",
    "OdooPage",
    "FormView",
    "ListView",
    "KanbanView",
]
