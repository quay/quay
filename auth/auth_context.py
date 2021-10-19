from flask import _request_ctx_stack


def get_authenticated_context():
    """
    Returns the auth context for the current request context, if any.
    """
    return getattr(_request_ctx_stack.top, "authenticated_context", None)


def get_authenticated_user():
    """
    Returns the authenticated user, if any, or None if none.
    """
    context = get_authenticated_context()
    return context.authed_user if context else None


def get_validated_oauth_token():
    """
    Returns the authenticated and validated OAuth access token, if any, or None if none.
    """
    context = get_authenticated_context()
    return context.authed_oauth_token if context else None


def set_authenticated_context(auth_context):
    """
    Sets the auth context for the current request context to that given.
    """
    ctx = _request_ctx_stack.top
    ctx.authenticated_context = auth_context
    return auth_context
