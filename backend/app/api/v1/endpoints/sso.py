"""Enterprise SSO via Google / Microsoft OAuth2 (Authlib)."""
import uuid

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.core.database import get_db
from app.models.sso import SsoAccount
from app.models.user import User

router = APIRouter(prefix="/sso", tags=["Enterprise SSO"])

_GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_MS_AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
_MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
_MS_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"


def _redirect_uri(provider: str) -> str:
    return settings.SSO_REDIRECT_URI.replace("/callback", f"/{provider}/callback")


@router.get("/google")
async def google_login() -> RedirectResponse:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google SSO not configured")
    client = AsyncOAuth2Client(
        client_id=settings.GOOGLE_CLIENT_ID,
        redirect_uri=_redirect_uri("google"),
        scope="openid email profile",
    )
    uri, _ = client.create_authorization_url(_GOOGLE_AUTHORIZE_URL)
    return RedirectResponse(uri)


@router.get("/google/callback")
async def google_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google SSO not configured")
    client = AsyncOAuth2Client(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=_redirect_uri("google"),
    )
    token = await client.fetch_token(_GOOGLE_TOKEN_URL, code=code)
    userinfo_resp = await client.get(_GOOGLE_USERINFO_URL)
    userinfo = userinfo_resp.json()
    return await _upsert_sso_user(db, "google", userinfo["sub"], userinfo.get("email"))


@router.get("/microsoft")
async def microsoft_login() -> RedirectResponse:
    if not settings.MICROSOFT_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Microsoft SSO not configured")
    client = AsyncOAuth2Client(
        client_id=settings.MICROSOFT_CLIENT_ID,
        redirect_uri=_redirect_uri("microsoft"),
        scope="openid email profile User.Read",
    )
    uri, _ = client.create_authorization_url(_MS_AUTHORIZE_URL)
    return RedirectResponse(uri)


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not settings.MICROSOFT_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Microsoft SSO not configured")
    client = AsyncOAuth2Client(
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        redirect_uri=_redirect_uri("microsoft"),
    )
    await client.fetch_token(_MS_TOKEN_URL, code=code)
    me_resp = await client.get(_MS_USERINFO_URL)
    me = me_resp.json()
    email = me.get("mail") or me.get("userPrincipalName")
    return await _upsert_sso_user(db, "microsoft", me["id"], email)


async def _upsert_sso_user(
    db: AsyncSession, provider: str, provider_uid: str, email: str | None
) -> dict:
    row = await db.execute(
        select(SsoAccount).where(
            SsoAccount.provider == provider,
            SsoAccount.provider_user_id == provider_uid,
        )
    )
    sso = row.scalar_one_or_none()

    if sso:
        user_row = await db.execute(select(User).where(User.id == sso.user_id))
        user = user_row.scalar_one_or_none()
    else:
        user = None
        if email:
            user_row = await db.execute(select(User).where(User.email == email))
            user = user_row.scalar_one_or_none()
        if not user:
            user = User(
                id=uuid.uuid4(),
                phone=f"sso_{provider}_{provider_uid[:12]}",
                country_code="00",
                email=email,
                is_active=True,
            )
            db.add(user)
            await db.flush()
        sso = SsoAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_uid,
            email=email,
        )
        db.add(sso)

    await db.commit()
    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer", "user_id": str(user.id)}
