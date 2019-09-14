from sqlalchemy import exists

from app import logger, session_scope
from app.Models import BlacklistedToken


class BlacklistedTokenController(object):
    @staticmethod
    def _id_exists(blacklist_id: str) -> bool:
        """ Checks database to see if a token is blacklisted.

        :param blacklist_id:    The aud:jti combination that makes up the blacklist_id
        :return:                True if blacklisted else False
        """
        with session_scope() as session:
            return session.query(exists().where(BlacklistedToken.id == blacklist_id)).scalar()

    def is_token_blacklisted(self, blacklist_id: str) -> bool:
        """ Public function for checking if a token is blacklisted

        :param blacklist_id:    The aud:jti combination that makes up the blacklist_id
        :return:                True if blacklisted else False
        """
        if self._id_exists(blacklist_id):
            logger.warning(f"Token pair {blacklist_id} is blacklisted.")
            return True
        else:
            return False

    def blacklist_token(self, blacklist_id: str, exp: int) -> None:
        """ Blacklist a token

        :param blacklist_id:    The aud:jti combination that makes up the blacklist_id
        :param exp:             The exp of the token, seconds from epoch.
        """
        if not self._id_exists(blacklist_id):
            token = BlacklistedToken(blacklist_id, exp)
            with session_scope() as session:
                session.add(token)
        else:
            logger.info(f"Token {blacklist_id} already blacklisted.")
