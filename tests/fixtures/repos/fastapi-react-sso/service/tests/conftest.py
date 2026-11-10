import os
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

os.environ["DATABASE_URL"] = "sqlite:///./test-team-insights.db"
os.environ["LLM_MODE"] = "fake"
os.environ["OIDC_ISSUER"] = "http://idp.test"

from fastapi.testclient import TestClient  # noqa: E402

from app import auth  # noqa: E402
from app.main import app  # noqa: E402

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
JWK = jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True) | {"kid": "test"}


@pytest.fixture(autouse=True)
def test_keys(monkeypatch):
    monkeypatch.setattr(auth, "signing_keys", lambda: jwt.PyJWKSet.from_dict({"keys": [JWK]}))


def token_for(groups: list[str], sub: str = "alice") -> str:
    now = int(time.time())
    claims = {
        "sub": sub, "groups": groups, "iss": "http://idp.test", "aud": "team-insights",
        "iat": now, "exp": now + 300,
    }
    return jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": "test"})


@pytest.fixture
def client():
    if os.path.exists("test-team-insights.db"):
        os.remove("test-team-insights.db")
    with TestClient(app) as c:
        yield c
