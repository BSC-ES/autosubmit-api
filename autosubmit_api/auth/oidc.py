from typing import Optional
import jwt
import requests
from autosubmit_api import config


def oidc_token_exchange(code: str, redirect_uri: Optional[str] = None) -> dict:
    """
    Exchange an OIDC code for an access token.
    Returns a dictionary of the response of the token exchange.
    """
    payload = "&".join(
        [
            f"client_id={config.OIDC_CLIENT_ID}",
            f"client_secret={config.OIDC_CLIENT_SECRET}",
            f"code={code}",
            "grant_type=authorization_code",
        ]
    )

    if redirect_uri:
        payload += f"&redirect_uri={redirect_uri}"

    resp_obj: dict = requests.post(
        config.OIDC_TOKEN_URL,
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    ).json()

    return resp_obj


def oidc_resolve_username(id_token: str, access_token: str) -> str:
    """
    Decides which claim to use as username and gets the username from
    the id_token or userinfo based on the configuration.
    """

    # Which claim to use as username
    oidc_username_claim = (
        config.OIDC_USERNAME_CLAIM if config.OIDC_USERNAME_CLAIM else "sub"
    )

    # Get username from id_token or userinfo
    if config.OIDC_USERNAME_SOURCE == "userinfo":
        # Get username from userinfo endpoint
        user_info: dict = requests.get(
            config.OIDC_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        ).json()
        username = user_info.get(oidc_username_claim)
    else:
        # Get username from id_token
        id_token_bytes = id_token.encode("utf-8")
        id_token_payload: dict = jwt.decode(
            id_token_bytes, options={"verify_signature": False}
        )
        username = id_token_payload.get(oidc_username_claim)

    return username
