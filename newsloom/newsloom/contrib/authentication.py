from rest_framework.authentication import SessionAuthentication as SessionAuthenticationBase


class SessionAuthentication(SessionAuthenticationBase):
    def enforce_csrf(self, request):
        return
