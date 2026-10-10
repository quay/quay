"""
CLI Authentication Endpoint using OAuth 2.0 Device Code Flow

This module provides a sophisticated CLI authentication mechanism that supports
all types of accounts (personal Microsoft accounts, work/school accounts) by
using the proper OAuth 2.0 Device Code Flow instead of ROPC.
"""

import logging

from flask import Blueprint, abort, jsonify, request

import features
from app import app, oauth_login
from auth.auth_context import get_authenticated_context
from auth.decorators import process_basic_auth
from oauth.oidc import DeviceCodeException, OIDCLoginService
from util.cache import no_cache

logger = logging.getLogger(__name__)

cli_auth = Blueprint("cli_auth", __name__)


@cli_auth.route("/cli/device/authorize", methods=["POST"])
@no_cache
def initiate_device_authorization():
    """
    Initiates device code flow for CLI authentication.
    Returns device code, user code, and verification URI.

    POST /cli/device/authorize
    Content-Type: application/x-www-form-urlencoded

    client_id=<client_id>&scope=openid profile email
    """
    client_id = request.values.get("client_id")
    scope = request.values.get("scope", "openid profile email")

    if not client_id:
        abort(400, description="Missing required parameter: client_id")

    # Find the OIDC service for this client
    oidc_service = None
    for service in oauth_login.services:
        if isinstance(service, OIDCLoginService) and service.client_id() == client_id:
            oidc_service = service
            break

    if not oidc_service:
        abort(400, description="Invalid client_id or OIDC not configured")

    try:
        # Initiate device code flow
        device_code_response = oidc_service.initiate_device_code_flow()

        # Return device code response to client
        return jsonify(
            {
                "device_code": device_code_response["device_code"],
                "user_code": device_code_response["user_code"],
                "verification_uri": device_code_response["verification_uri"],
                "verification_uri_complete": device_code_response.get("verification_uri_complete"),
                "expires_in": device_code_response.get("expires_in", 300),
                "interval": device_code_response.get("interval", 5),
            }
        )

    except DeviceCodeException as e:
        logger.exception("Device code initiation failed")
        abort(400, description=f"Device code flow failed: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error during device code initiation")
        abort(500, description="Internal server error")


@cli_auth.route("/cli/device/token", methods=["POST"])
@no_cache
def exchange_device_token():
    """
    Exchanges device code for access token after user authorization.

    POST /cli/device/token
    Content-Type: application/x-www-form-urlencoded

    grant_type=urn:ietf:params:oauth:grant-type:device_code&
    client_id=<client_id>&
    device_code=<device_code>
    """
    grant_type = request.values.get("grant_type")
    client_id = request.values.get("client_id")
    device_code = request.values.get("device_code")

    # Validate parameters
    if grant_type != "urn:ietf:params:oauth:grant-type:device_code":
        abort(400, description="Invalid grant_type")

    if not client_id or not device_code:
        abort(400, description="Missing required parameters")

    # Find the OIDC service
    oidc_service = None
    for service in oauth_login.services:
        if isinstance(service, OIDCLoginService) and service.client_id() == client_id:
            oidc_service = service
            break

    if not oidc_service:
        abort(400, description="Invalid client_id")

    try:
        # Poll for token (single attempt - client should handle polling)
        token_response = oidc_service.poll_for_token(device_code, interval=0, max_attempts=1)

        return jsonify(
            {
                "access_token": token_response["access_token"],
                "token_type": token_response.get("token_type", "Bearer"),
                "expires_in": token_response.get("expires_in", 3600),
                "id_token": token_response.get("id_token"),
                "refresh_token": token_response.get("refresh_token"),
                "scope": token_response.get("scope"),
            }
        )

    except DeviceCodeException as e:
        error_message = str(e)
        if "authorization_pending" in error_message:
            # User hasn't authorized yet
            return (
                jsonify(
                    {
                        "error": "authorization_pending",
                        "error_description": "The authorization request is still pending.",
                    }
                ),
                400,
            )
        elif "slow_down" in error_message:
            # Client is polling too fast
            return (
                jsonify(
                    {
                        "error": "slow_down",
                        "error_description": "The client is polling too frequently.",
                    }
                ),
                400,
            )
        elif "access_denied" in error_message:
            # User denied authorization
            return (
                jsonify(
                    {
                        "error": "access_denied",
                        "error_description": "The user denied the authorization request.",
                    }
                ),
                400,
            )
        elif "expired_token" in error_message:
            # Device code expired
            return (
                jsonify(
                    {"error": "expired_token", "error_description": "The device code has expired."}
                ),
                400,
            )
        else:
            # Other error
            logger.exception("Device token exchange failed")
            return (
                jsonify(
                    {
                        "error": "invalid_grant",
                        "error_description": f"Token exchange failed: {error_message}",
                    }
                ),
                400,
            )

    except Exception as e:
        logger.exception("Unexpected error during device token exchange")
        abort(500, description="Internal server error")


@cli_auth.route("/cli/auth", methods=["POST"])
@no_cache
def cli_authenticate():
    """
    Initiate CLI authentication using device code flow.
    This endpoint provides a non-blocking interface for CLI clients.

    POST /cli/auth
    Content-Type: application/x-www-form-urlencoded

    client_id=<client_id>&scope=openid profile email

    Returns device code and instructions for completing authentication.
    """
    client_id = request.values.get("client_id")
    scope = request.values.get("scope", "openid profile email")

    if not client_id:
        abort(400, description="Missing required parameter: client_id")

    # Find the OIDC service
    oidc_service = None
    for service in oauth_login.services:
        if isinstance(service, OIDCLoginService) and service.client_id() == client_id:
            oidc_service = service
            break

    if not oidc_service:
        abort(400, description="Invalid client_id or OIDC not configured")

    try:
        # Initiate device code flow (non-blocking)
        device_code_response = oidc_service.initiate_device_code_flow()

        user_code = device_code_response["user_code"]
        verification_uri = device_code_response["verification_uri"]
        verification_uri_complete = device_code_response.get("verification_uri_complete")
        device_code = device_code_response["device_code"]
        expires_in = device_code_response.get("expires_in", 900)
        interval = device_code_response.get("interval", 5)

        # Format the instructions clearly
        instructions = []
        instructions.append("🔐 AUTHENTICATION REQUIRED")
        instructions.append("")
        instructions.append("Complete these steps to authenticate:")
        instructions.append("")
        instructions.append(f"1. Visit: {verification_uri}")
        if verification_uri_complete:
            instructions.append(f"   Or visit: {verification_uri_complete}")
        instructions.append(f"2. Enter code: {user_code}")
        instructions.append("3. Complete authentication in your browser")
        instructions.append("4. Run the polling command below to get your Docker token")
        instructions.append("")
        instructions.append("POLLING COMMAND:")
        instructions.append(f"curl -X POST http://localhost:8080/oauth2/cli/token \\")
        instructions.append(f'     -d "client_id={client_id}" \\')
        instructions.append(f'     -d "device_code={device_code}"')
        instructions.append("")
        instructions.append(f"⏰ You have {expires_in // 60} minutes to complete authentication")
        instructions.append(f"🔄 Poll every {interval} seconds until you get a token")

        return jsonify(
            {
                "success": True,
                "device_code": device_code,
                "user_code": user_code,
                "verification_uri": verification_uri,
                "verification_uri_complete": verification_uri_complete,
                "expires_in": expires_in,
                "interval": interval,
                "instructions": "\n".join(instructions),
                "poll_url": f"http://localhost:8080/oauth2/cli/token",
                "poll_data": {"client_id": client_id, "device_code": device_code},
            }
        )

    except DeviceCodeException as e:
        logger.exception("CLI authentication initiation failed")
        return (
            jsonify(
                {"success": False, "error": "authentication_failed", "error_description": str(e)}
            ),
            400,
        )

    except Exception as e:
        logger.exception("Unexpected error during CLI authentication initiation")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "internal_error",
                    "error_description": f"Internal server error: {str(e)}",
                }
            ),
            500,
        )


@cli_auth.route("/cli/token", methods=["POST"])
@no_cache
def cli_get_token():
    """
    Complete CLI authentication and generate App-Specific Token.
    This endpoint polls for device code completion and returns the token.

    POST /cli/token
    Content-Type: application/x-www-form-urlencoded

    client_id=<client_id>&device_code=<device_code>

    Returns app-specific token for Docker CLI use.
    """
    client_id = request.values.get("client_id")
    device_code = request.values.get("device_code")

    if not client_id or not device_code:
        abort(400, description="Missing required parameters: client_id and device_code")

    # Find the OIDC service
    oidc_service = None
    for service in oauth_login.services:
        if isinstance(service, OIDCLoginService) and service.client_id() == client_id:
            oidc_service = service
            break

    if not oidc_service:
        abort(400, description="Invalid client_id or OIDC not configured")

    try:
        from data import model

        # Poll for token (single attempt - client should handle polling)
        try:
            token_response = oidc_service.poll_for_token(device_code, interval=0, max_attempts=1)
        except DeviceCodeException as e:
            error_message = str(e)
            if "authorization_pending" in error_message.lower():
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "authorization_pending",
                            "error_description": "Still waiting for user to complete authentication in browser. Keep polling.",
                        }
                    ),
                    202,
                )  # 202 Accepted - still processing
            elif "access_denied" in error_message.lower():
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "access_denied",
                            "error_description": "User denied the authorization request.",
                        }
                    ),
                    400,
                )
            elif "expired_token" in error_message.lower():
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "expired_token",
                            "error_description": "Device code has expired. Start authentication again.",
                        }
                    ),
                    400,
                )
            else:
                raise  # Re-raise for other errors

        # Process the token response and get user info
        access_token = token_response["access_token"]
        id_token = token_response.get("id_token")

        # Use the existing exchange_code_for_login method which handles user creation
        try:
            if id_token:
                # Decode ID token for basic user info
                decoded_id_token = oidc_service.decode_user_jwt(id_token)
                user_info = decoded_id_token.copy()

                # Get additional user info if available
                if oidc_service.user_endpoint():
                    try:
                        additional_user_info = oidc_service.get_user_info(
                            oidc_service._http_client, access_token
                        )
                        user_info.update(additional_user_info)
                    except Exception as e:
                        logger.warning(f"Failed to get additional user info: {e}")

                # Extract user information
                lid = user_info.get("sub", "")
                lemail = user_info.get("email", "")
                lusername = (
                    user_info.get("preferred_username")
                    or user_info.get("upn")
                    or lemail.split("@")[0]
                )

            else:
                # No ID token, use userinfo endpoint
                if not oidc_service.user_endpoint():
                    raise DeviceCodeException(
                        "No ID token provided and no userinfo endpoint available"
                    )

                user_info = oidc_service.get_user_info(oidc_service._http_client, access_token)
                lid = user_info.get("sub", "")
                lemail = user_info.get("email", "")
                lusername = (
                    user_info.get("preferred_username")
                    or user_info.get("upn")
                    or lemail.split("@")[0]
                )

        except Exception as token_error:
            logger.exception(f"Error processing token response: {token_error}")
            raise DeviceCodeException(f"Failed to process authentication tokens: {token_error}")

        # Find or create user in database
        user_obj = model.user.get_nonrobot_user(lusername) or model.user.find_user_by_email(lemail)
        if not user_obj and lemail:
            # Create user if they don't exist
            try:
                user_obj = model.user.create_user_noverify(lusername, lemail)
                logger.info(f"Created new user via device code auth: {lusername}/{lemail}")
            except Exception as create_error:
                logger.warning(f"Failed to create user {lusername}/{lemail}: {create_error}")
                # Try with a slightly different username if there's a conflict
                try:
                    import uuid

                    alt_username = f"{lusername}_{str(uuid.uuid4())[:8]}"
                    user_obj = model.user.create_user_noverify(alt_username, lemail)
                    lusername = alt_username
                    logger.info(f"Created user with alternative username: {lusername}")
                except:
                    pass

        if not user_obj:
            raise Exception(f"Unable to find or create user: {lusername} / {lemail}")

        # Generate App-Specific Token for Docker CLI use
        if features.APP_SPECIFIC_TOKENS:
            try:
                app_token = model.appspecifictoken.create_token(
                    user_obj, "CLI Authentication Token (Auto-generated)"
                )
                full_token = model.appspecifictoken.get_full_token_string(app_token)

                instructions = []
                instructions.append("🎉 Authentication successful!")
                instructions.append("")
                instructions.append("Use this token for Docker CLI:")
                instructions.append("")
                instructions.append("docker login localhost:8080")
                instructions.append(f"Username: $app")
                instructions.append(f"Password: {full_token}")
                instructions.append("")
                instructions.append("💡 Save this token - it can be reused for future Docker logins")

                return jsonify(
                    {
                        "success": True,
                        "user": {"id": lid, "username": lusername, "email": lemail},
                        "app_token": {
                            "token": full_token,
                            "username": "$app",
                            "title": app_token.title,
                            "created": app_token.created.isoformat(),
                        },
                        "docker_login": {"username": "$app", "password": full_token},
                        "instructions": "\n".join(instructions),
                    }
                )

            except Exception as token_error:
                logger.warning(f"Failed to create app-specific token: {token_error}")

        # Fallback response without app-specific token
        return jsonify(
            {
                "success": True,
                "user": {"id": lid, "username": lusername, "email": lemail},
                "message": (
                    f"🎉 Authentication successful for {lemail}!\n\n"
                    f"Note: App-specific tokens are not enabled. "
                    f"Contact your administrator to enable FEATURE_APP_SPECIFIC_TOKENS "
                    f"for seamless Docker CLI integration."
                ),
            }
        )

    except DeviceCodeException as e:
        logger.exception("CLI token retrieval failed")
        return (
            jsonify(
                {"success": False, "error": "authentication_failed", "error_description": str(e)}
            ),
            400,
        )

    except Exception as e:
        logger.exception("Unexpected error during CLI token retrieval")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "internal_error",
                    "error_description": f"Internal server error: {str(e)}",
                }
            ),
            500,
        )


# Register the CLI auth blueprint
app.register_blueprint(cli_auth, url_prefix="/oauth2")
