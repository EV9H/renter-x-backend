from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow authors of a post/comment to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the author
        return obj.author == request.user

class IsModerator(permissions.BasePermission):
    """
    Custom permission to allow moderators to manage content.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff