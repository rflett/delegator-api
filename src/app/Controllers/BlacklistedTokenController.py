from app import DBSession
from app.Models import BlacklistedToken
from sqlalchemy import exists

session = DBSession()


def id_exists(blacklist_id: str) -> bool:
    """ Checks database to see if token is blacklisted. """
    return session.query(exists().where(BlacklistedToken.id == blacklist_id)).scalar()


class BlacklistedTokenController(object):

    @staticmethod
    def is_token_blacklisted(blacklist_id: str) -> bool:
        """ Checks to see if a token is blacklisted. """
        return id_exists(blacklist_id)

    @staticmethod
    def blacklist_token(blacklist_id: str, exp: int):
        """ Blacklist token if it isn't already blacklisted. """
        if not id_exists(blacklist_id):
            token = BlacklistedToken(blacklist_id, exp)
            session.add(token)
            session.commit()
