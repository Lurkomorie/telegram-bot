"""
Custom admin actions for bulk operations
"""
from sqladmin import action
from starlette.requests import Request
from starlette.responses import RedirectResponse


# This will be added as methods to each ModelView class
# SQLAdmin actions work synchronously with the session
