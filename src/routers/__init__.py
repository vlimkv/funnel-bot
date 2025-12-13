# src/routers/__init__.py

from .admin import router as admin_router
from .subscription import router as subscription_router
from .user import router as user_router

all_routers = [admin_router, subscription_router, user_router]