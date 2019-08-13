from sqlalchemy import exists

from app import logger, session_scope
from app.Models import BlacklistedToken


def id_exists(blacklist_id: str) -> bool:
    """ Checks database to see if a token is blacklisted.

    :param blacklist_id:    The aud:jti combination that makes up the blacklist_id
    :return:                True if blacklisted else False
    """
    with session_scope() as session:
        ret = session.query(exists().where(BlacklistedToken.id == blacklist_id)).scalar()
        return ret


class BlacklistedTokenController(object):
    @staticmethod
    def is_token_blacklisted(blacklist_id: str) -> bool:
        """ Public function for checking if a token is blacklisted

        :param blacklist_id:    The aud:jti combination that makes up the blacklist_id
        :return:                True if blacklisted else False
        """
        if id_exists(blacklist_id):
            logger.warning(f"Token pair {blacklist_id} is blacklisted.")
            return True
        else:
            return False

    @staticmethod
    def blacklist_token(blacklist_id: str, exp: int) -> None:
        """ Blacklist a token

        :param blacklist_id:    The aud:jti combination that makes up the blacklist_id
        :param exp:             The exp of the token, seconds from epoch.
        """
        if not id_exists(blacklist_id):
            token = BlacklistedToken(blacklist_id, exp)
            with session_scope() as session:
                session.add(token)
        else:
            logger.info(f"Token {blacklist_id} already blacklisted.")
