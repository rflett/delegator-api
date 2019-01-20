from app import DBSession
from app.Models import BlacklistedToken
from sqlalchemy import exists

session = DBSession()


def id_exists(blacklist_id: str) -> bool:
    """ 
    Checks database to see if token is blacklisted. 
    
    :param blacklist_id str: The aud:jti combination the is a blacklist_id

    :return: True if blacklisted or False
    """
    return session.query(exists().where(BlacklistedToken.id == blacklist_id)).scalar()


class BlacklistedTokenController(object):

    @staticmethod
    def is_token_blacklisted(blacklist_id: str) -> bool:
        """ 
        Checks to see if a token is blacklisted. Just calls the helper function.

        :param blacklist_id str: The aud:jti combination the is a blacklist_id

        :return: True if blacklisted or False
        """
        return id_exists(blacklist_id)

    @staticmethod
    def blacklist_token(blacklist_id: str, exp: int):
        """ 
        Blacklist a token if it isn't already blacklisted. 
        
        :param blacklist_id str:    The aud:jti combination the is a blacklist_id
        :param exp int:             The expiration of the token. datetime object as int.
        """
        if not id_exists(blacklist_id):
            token = BlacklistedToken(blacklist_id, exp)
            session.add(token)
            session.commit()
