from django.contrib.auth import get_user_model
from ninja.security import HttpBearer

from .token import decode

User = get_user_model()


class JwtAuth(HttpBearer):
    def authenticate(self, request, token):
        results = decode(token)

        if results is None:
            return None

        if results.get("token_type") != "access":
            return None

        user = User.objects.filter(id=results.get("sub"), is_active=True).first()

        if user is None:
            return None

        if results.get("ver") != user.token_version:
            return None

        request.user = user

        return user