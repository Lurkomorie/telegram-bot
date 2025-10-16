"""
Admin panel authentication backend for Starlette-Admin
"""
import secrets
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminConfig, AdminUser, AuthProvider
from starlette_admin.exceptions import FormValidationError, LoginFailed
from app.settings import settings


class AdminAuth(AuthProvider):
    """Basic authentication for Starlette-Admin"""
    
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        """Handle login request"""
        # Validate credentials using constant-time comparison
        username_valid = secrets.compare_digest(username, settings.ADMIN_USERNAME)
        password_valid = secrets.compare_digest(password, settings.ADMIN_PASSWORD)
        
        if not (username_valid and password_valid):
            raise LoginFailed("Invalid username or password")
        
        # Store authentication in session
        request.session.update({"username": username})
        return response
    
    async def is_authenticated(self, request: Request) -> bool:
        """Check if user is authenticated"""
        return request.session.get("username") == settings.ADMIN_USERNAME
    
    def get_admin_config(self, request: Request) -> AdminConfig:
        """Get admin configuration"""
        user = request.session.get("username", "guest")
        return AdminConfig(
            app_title="Telegram Bot Admin",
            logo_url=None,
        )
    
    def get_admin_user(self, request: Request) -> AdminUser:
        """Get current admin user"""
        user = request.session.get("username", "guest")
        return AdminUser(username=user)
    
    async def logout(self, request: Request, response: Response) -> Response:
        """Handle logout request"""
        request.session.clear()
        return response
