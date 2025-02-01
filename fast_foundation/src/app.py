import logging
from fastapi import FastAPI, HTTPException, Security, Request, Depends
from fast_foundation.src.settings import LOGGING_CONFIG, settings
import uvicorn
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED
from jose.jwk import construct
from jose import jwt
from fast_foundation.src.security import fetch_token, oauth2_scheme
from fastapi.staticfiles import StaticFiles
import aiohttp

logger = logging.getLogger(__name__)
logging.config.dictConfig(LOGGING_CONFIG)
allowed_origins = settings.ALLOWED_ORIGINS.split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The first part of the function, before the yield, will be executed before the application starts.
    logger.info("Application is started")
    logger.info(f"Getting OIDC_CONFIG from: {settings.OIDC_URL}")
    async with aiohttp.ClientSession() as client:
        oidc_config = await client.get(settings.OIDC_CONFIG_URL)
        oidc_config.raise_for_status()
        z = await oidc_config.json()
        app.state.oidc_config = z
        logger.info(f"OIDC is configured.")

    yield
    # And the part after the yield will be executed after the application has finished.
    logger.info("Application is closed")


app = FastAPI(lifespan=lifespan)
app.mount(
    "/static", StaticFiles(directory="fast_foundation/static", html=True), name="static"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        if not hasattr(app.state, "sessions"):
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="app.state is not found. Omid error.",
            )
        # if not hasattr(app.state.sessions, token):
        #     raise HTTPException(
        #         status_code=HTTP_401_UNAUTHORIZED,
        #         detail="Invalid token: token format not intact.",
        #     )
        # Fetch JWKS from the discovery document
        jwks_url = app.state.oidc_config["jwks_uri"]
        async with aiohttp.ClientSession() as client:
            jwks = await client.get(jwks_url)
            # jwks.raise_for_status()
            jwks_json = await jwks.json()

        # Decode the token to get the 'kid' (Key ID) from the header
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")

        # Find the correct key from JWKS using 'kid'
        key = next((k for k in jwks_json["keys"] if k["kid"] == kid), None)
        if key is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token: Key not found"
            )
        # Construct the public key for verification
        public_key = construct(key)

        ## session_token coming from user session and loging info stored in app.state
        # Decode and verify token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            access_token=app.state.sessions[token],
            options={
                "verify_aud": False,  # Set to True if you want to verify audience
                "verify_at_hash": True,  # Add this to disable at_hash validation
            },
        )

        # Additional checks on payload if needed
        if payload.get("iss") != settings.OIDC_URL:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Invalid issuer"
            )

        return payload
    except jwt.JWTError as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )


@app.get("/")
async def get():
    return {"Hello": "World"}


@app.get("/protected")
async def protected_route(
    current_user: dict = Security(get_current_user, scopes=["authors"])
):
    return {"message": "This is a protected route", "user": current_user}


@app.get("/oidc-config")
async def oidc_config():
    return app.state.oidc_config


@app.get("/callback")
async def callback(code: str, request: Request):

    logger.info("New /callback recieved.")
    token = await fetch_token(code, f"{request.base_url}callback")
    logger.info("Token fetched.")

    if not hasattr(app.state, "sessions"):
        app.state.sessions = {}
    app.state.sessions[token["id_token"]] = token["access_token"]
    logger.info("id_token saved.")
    return token


def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("fast_foundation.src.app:app", host="0.0.0.0", port=8000, reload=True)
