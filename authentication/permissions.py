from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsAgent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_agent


class IsAdminOrAgent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (request.user.is_admin or request.user.is_agent)


class IsNormalUser(permissions.BasePermission):
    """Permission class to restrict access to normal users only (game platform)"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_normal_user

