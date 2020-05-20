from app.Extensions.Database import db


class JWTBlacklist(db.Model):
    __tablename__ = "jwt_blacklists"

    jti = db.Column("jti", db.String, primary_key=True)
    exp = db.Column("exp", db.Integer)

    def __init__(self, jti: str, exp: int):
        self.jti = jti
        self.exp = exp

    def as_dict(self) -> dict:
        """dict repr of a JWTBlacklist object"""
        return {"jti": self.jti, "exp": self.exp}
