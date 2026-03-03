"""OAuth authentication flow for Square CLI."""

from __future__ import annotations

import hashlib
import os
import secrets
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from rich.console import Console

from . import config as cfg

console = Console()

# Square OAuth endpoints
AUTHORIZE_URL = "https://connect.squareup.com/oauth2/authorize"
TOKEN_URL = "https://connect.squareup.com/oauth2/token"
REVOKE_URL = "https://connect.squareup.com/oauth2/revoke"

SANDBOX_AUTHORIZE_URL = "https://connect.squareupsandbox.com/oauth2/authorize"
SANDBOX_TOKEN_URL = "https://connect.squareupsandbox.com/oauth2/token"

# OAuth scopes for business operations
DEFAULT_SCOPES = [
    "ITEMS_READ",
    "ITEMS_WRITE",
    "ORDERS_READ",
    "ORDERS_WRITE",
    "PAYMENTS_READ",
    "PAYMENTS_WRITE",
    "CUSTOMERS_READ",
    "CUSTOMERS_WRITE",
    "INVENTORY_READ",
    "INVENTORY_WRITE",
    "EMPLOYEES_READ",
    "TIMECARDS_READ",
    "MERCHANT_PROFILE_READ",
    "LOYALTY_READ",
    "LOYALTY_WRITE",
    "GIFTCARDS_READ",
    "GIFTCARDS_WRITE",
    "INVOICES_READ",
    "INVOICES_WRITE",
    "SUBSCRIPTIONS_READ",
    "SUBSCRIPTIONS_WRITE",
    "DISPUTES_READ",
    "BANK_ACCOUNTS_READ",
    "PAYOUTS_READ",
    "DEVICE_CREDENTIAL_MANAGEMENT",
    "VENDOR_READ",
    "VENDOR_WRITE",
]

# Placeholder — to be replaced with a real Square app client_id
# Users can also set SQUARE_CLIENT_ID env var
CLIENT_ID_PLACEHOLDER = "REPLACE_WITH_YOUR_SQUARE_APP_CLIENT_ID"


def get_client_id() -> str:
    """Get the OAuth client_id from env var or embedded default."""
    return os.environ.get("SQUARE_CLIENT_ID", CLIENT_ID_PLACEHOLDER)


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = hashlib.sha256(verifier.encode("ascii")).digest()
    # base64url encode without padding
    import base64

    challenge_b64 = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode("ascii")
    return verifier, challenge_b64


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def login(
    profile: str = "default",
    sandbox: bool = False,
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    """Run the OAuth authorization code flow with PKCE.

    Opens the user's browser to Square's authorization page.
    Starts a local HTTP server to receive the callback.
    Exchanges the auth code for tokens and stores them in the keychain.

    Returns:
        Dict with merchant_id, access_token expiry info, etc.
    """
    client_id = get_client_id()
    if client_id == CLIENT_ID_PLACEHOLDER:
        console.print(
            "[yellow]Warning:[/] No Square app client_id configured.\n"
            "Set SQUARE_CLIENT_ID env var or create an app at "
            "https://developer.squareup.com/apps\n"
            "\nFor now, you can authenticate with an access token:\n"
            "  [bold]export SQUARE_ACCESS_TOKEN=your_token_here[/]\n"
        )
        raise SystemExit(1)

    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(32)
    port = _find_free_port()
    redirect_uri = f"http://localhost:{port}/callback"

    authorize_base = SANDBOX_AUTHORIZE_URL if sandbox else AUTHORIZE_URL
    token_base = SANDBOX_TOKEN_URL if sandbox else TOKEN_URL

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes or DEFAULT_SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "response_type": "code",
    }

    auth_url = f"{authorize_base}?{urlencode(params)}"

    # State shared between the callback handler and this function
    callback_result: dict[str, Any] = {}
    server_ready = threading.Event()
    callback_received = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)

            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return

            received_state = qs.get("state", [None])[0]
            if received_state != state:
                callback_result["error"] = "State mismatch — possible CSRF attack"
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Error: State mismatch. Please try again.")
                callback_received.set()
                return

            if "error" in qs:
                callback_result["error"] = qs["error"][0]
                callback_result["error_description"] = qs.get("error_description", [""])[0]
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authorization denied. You can close this tab.")
                callback_received.set()
                return

            code = qs.get("code", [None])[0]
            if not code:
                callback_result["error"] = "No authorization code received"
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Error: No code received.")
                callback_received.set()
                return

            callback_result["code"] = code
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Authorized!</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )
            callback_received.set()

        def log_message(self, format, *args):
            pass  # Suppress default HTTP server logging

    server = HTTPServer(("127.0.0.1", port), CallbackHandler)

    def serve():
        server_ready.set()
        server.handle_request()  # Handle exactly one request

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    server_ready.wait()

    console.print("[bold]Opening browser to authorize with Square...[/]")
    console.print(f"[dim]If the browser doesn't open, visit:\n{auth_url}[/]\n")
    webbrowser.open(auth_url)

    console.print("Waiting for authorization...", end=" ")
    callback_received.wait(timeout=300)  # 5 minute timeout

    if not callback_received.is_set():
        console.print("[red]Timed out[/]")
        raise SystemExit(1)

    if "error" in callback_result:
        console.print(f'[red]Failed: {callback_result["error"]}[/]')
        if "error_description" in callback_result:
            console.print(f'  {callback_result["error_description"]}')
        raise SystemExit(1)

    console.print("[green]Received![/]")

    # Exchange code for tokens
    console.print("Exchanging code for tokens...", end=" ")
    token_response = httpx.post(
        token_base,
        json={
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": callback_result["code"],
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )

    if token_response.status_code != 200:
        console.print("[red]Failed[/]")
        console.print(f"  Token exchange error: {token_response.text}")
        raise SystemExit(1)

    token_data = token_response.json()
    console.print("[green]Done![/]")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    merchant_id = token_data.get("merchant_id")
    expires_at = token_data.get("expires_at")

    # Store tokens in keychain
    if access_token:
        cfg.save_access_token(access_token, profile=profile)
    if refresh_token:
        cfg.save_refresh_token(refresh_token, profile=profile)

    # Save profile config
    env = "sandbox" if sandbox else "production"
    profile_data: dict[str, Any] = {"environment": env}
    if merchant_id:
        profile_data["merchant_id"] = merchant_id
    cfg.save_config(profile_data, profile=profile)

    return {
        "merchant_id": merchant_id,
        "expires_at": expires_at,
        "environment": env,
        "profile": profile,
    }


def logout(profile: str = "default") -> None:
    """Clear stored credentials for a profile."""
    cfg.delete_tokens(profile=profile)
    console.print(f'Logged out of profile "{profile}".')


def refresh_access_token(profile: str = "default", sandbox: bool = False) -> str | None:
    """Use the refresh token to get a new access token."""
    refresh_token = cfg.get_refresh_token(profile)
    if not refresh_token:
        return None

    client_id = get_client_id()
    token_url = SANDBOX_TOKEN_URL if sandbox else TOKEN_URL

    response = httpx.post(
        token_url,
        json={
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )

    if response.status_code != 200:
        return None

    data = response.json()
    new_access = data.get("access_token")
    new_refresh = data.get("refresh_token")

    if new_access:
        cfg.save_access_token(new_access, profile=profile)
    if new_refresh:
        cfg.save_refresh_token(new_refresh, profile=profile)

    return new_access
