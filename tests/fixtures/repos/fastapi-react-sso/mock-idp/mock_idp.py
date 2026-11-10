"""A mock OpenID Connect identity provider for local runs. Never use it in production."""

import os
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ISSUER = os.environ.get("MOCK_IDP_ISSUER", "http://localhost:9000")
AUDIENCE = "team-insights"
USERS = {
    "alice": ["ti-analysts"],
    "bob": ["ti-viewers"],
    "carol": ["ti-admins"],
}

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KID = uuid.uuid4().hex[:8]
app = FastAPI(title="Mock IdP")


@app.get("/.well-known/openid-configuration")
def discovery() -> dict:
    return {"issuer": ISSUER, "jwks_uri": f"{ISSUER}/jwks", "token_endpoint": f"{ISSUER}/token"}


@app.get("/jwks")
def jwks() -> dict:
    public = jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True)
    return {"keys": [public | {"kid": KID, "use": "sig", "alg": "RS256"}]}


class SignIn(BaseModel):
    username: str


@app.post("/token")
def token(body: SignIn) -> dict:
    username = body.username
    if username not in USERS:
        raise HTTPException(401, "unknown user")
    now = int(time.time())
    claims = {
        "sub": username, "groups": USERS[username], "iss": ISSUER, "aud": AUDIENCE,
        "iat": now, "exp": now + 3600,
    }
    access = jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": KID})
    return {"access_token": access, "token_type": "Bearer", "expires_in": 3600}
