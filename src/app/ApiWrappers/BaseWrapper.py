import datetime
import uuid

import jwt


class BaseWrapper(object):
    def __init__(self, jwt_secret: str, url: str):
        self.url = url
        self._jwt_secret = jwt_secret

    def create_sa_token(self) -> str:
        """Create a JWT token to make requests to other services"""
        return jwt.encode(
            payload={
                "claims": {"type": "service-account", "service-account-name": "delegator-api"},
                "jti": str(uuid.uuid4()),
                "aud": "delegator.com.au",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=30),
            },
            key=self._jwt_secret,
            algorithm="HS256",
        ).decode("utf-8")
