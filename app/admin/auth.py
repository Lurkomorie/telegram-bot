"""
Admin panel authentication backend
"""
import secrets
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from app.settings import settings


class AdminAuth(AuthenticationBackend):
    """Basic authentication for admin panel"""
    
    async def login(self, request: Request) -> bool:
        """Handle login request"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        
        # Validate credentials using constant-time comparison
        username_valid = secrets.compare_digest(username, settings.ADMIN_USERNAME)
        password_valid = secrets.compare_digest(password, settings.ADMIN_PASSWORD)
        
        if username_valid and password_valid:
            # Store authentication status in session
            request.session.update({"authenticated": True})
            return True
        
        return False
    
    async def logout(self, request: Request) -> bool:
        """Handle logout request"""
        request.session.clear()
        return True
    
    async def authenticate(self, request: Request) -> bool:
        """Check if user is authenticated"""
        return request.session.get("authenticated", False)

