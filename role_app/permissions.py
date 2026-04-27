from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = 'Access denied. Admin role required.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role is not None
            and request.user.role.name == 'ADMIN'
        )

