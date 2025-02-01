# dex.py
import aiohttp
from fast_foundation.src.config import settings
from fastapi.security import OAuth2AuthorizationCodeBearer

# OAuth2 scheme for token validation
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{settings.OIDC_URL}/auth",
    tokenUrl=f"{settings.OIDC_URL}/token",
    scopes={
        "email": "This is openid scope",
        "openid": "This is openid scope",
        "groups": "oidc groups",
    },
    refreshUrl=f"{settings.OIDC_URL}/token",
    auto_error=False,
)


async def fetch_token(code: str, redirect_uri: str):
    async with aiohttp.ClientSession() as client:
        response = await client.post(
            f"{settings.OIDC_URL}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.CLIENT_ID,
                "client_secret": settings.CLIENT_SECRET,
            },
        )
        return await response.json()
