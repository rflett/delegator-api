import typing
from app import DBSession
from app.Models import BlacklistedToken
from sqlalchemy import exists

session = DBSession()


def id_exists(id: str) -> bool:
    return session.query(exists().where(BlacklistedToken.id == id)).scalar()


class BlacklistedTokenController(object):

    @staticmethod
    def is_token_blacklisted(id: str) -> bool:
        return id_exists(id)

    @staticmethod
    def blacklist_token(id: str):
        """ Blacklist token if it isn't already blacklisted"""
        if not id_exists(id):
            token = BlacklistedToken(id)
            session.add(token)
            session.commit()
