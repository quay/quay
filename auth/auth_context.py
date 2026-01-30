from flask import _request_ctx_stack, request, session


def get_authenticated_context():
    """
    Returns the auth context for the current request context, if any.
    """
    return getattr(_request_ctx_stack.top, "authenticated_context", None)


def determine_auth_type_and_performer_kind(auth_context=None, oauth_token=None):
    """
    Determines the authentication type and performer kind from the current request context.

    This is a shared helper to ensure consistent auth detection across all logging paths.

    Args:
        auth_context: Optional pre-fetched auth context. If None, will be fetched.
        oauth_token: Optional pre-fetched OAuth token. Used to detect OAuth auth type.

    Returns:
        tuple: (auth_type, performer_kind) where:
            - auth_type: One of 'oauth', 'app_specific_token', 'sso', 'token', 'bearer',
                         'basic', 'session', or 'anonymous'
            - performer_kind: One of 'oauth', 'app_specific_token', 'robot', 'token',
                              'user', or 'anonymous'
    """
    auth_type = None
    performer_kind = None

    # Check OAuth token first (most specific)
    if oauth_token:
        auth_type = "oauth"
        performer_kind = "oauth"

    # Get auth context if not provided
    if auth_context is None:
        auth_context = get_authenticated_context()

    # Determine from auth context
    # Use getattr with defaults to handle both ValidatedAuthContext and SignedAuthContext
    # (SignedAuthContext doesn't have these attributes directly)
    if auth_context and not auth_type:
        if getattr(auth_context, "appspecifictoken", None):
            auth_type = "app_specific_token"
            performer_kind = "app_specific_token"
        elif getattr(auth_context, "oauthtoken", None):
            auth_type = "oauth"
            performer_kind = "oauth"
        elif getattr(auth_context, "token", None):
            auth_type = "token"
            performer_kind = "token"
        elif getattr(auth_context, "sso_token", None):
            auth_type = "sso"
            performer_kind = "user"
        elif getattr(auth_context, "user", None):
            performer_kind = "user"

        # Preserve robot identity while keeping auth_type from token-based auth
        # This must be checked separately so robot auth via OAuth/token still sets auth_type
        if getattr(auth_context, "robot", None):
            performer_kind = "robot"

    # Fall back to Authorization header if auth_type not yet determined
    # Wrapped in try/except to handle calls outside request context (e.g., background workers)
    if not auth_type:
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header:
                auth_lower = auth_header.lower()
                if auth_lower.startswith("bearer "):
                    auth_type = "bearer"
                elif auth_lower.startswith("basic "):
                    auth_type = "basic"
            elif session.get("login_time"):
                # Session-based authentication (web UI)
                auth_type = "session"
        except RuntimeError:
            # Outside request context no action taken(e.g., background worker)
            pass

    # Default to anonymous if nothing detected
    if not auth_type:
        auth_type = "anonymous"
    if not performer_kind:
        performer_kind = "anonymous"

    return auth_type, performer_kind


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


def get_sso_token():
    """
    Returns the authenticated and SSO token, if any, or None if none.
    """
    context = get_authenticated_context()
    return context.sso_token if context else None


def set_authenticated_context(auth_context):
    """
    Sets the auth context for the current request context to that given.
    """
    ctx = _request_ctx_stack.top
    ctx.authenticated_context = auth_context
    return auth_context
