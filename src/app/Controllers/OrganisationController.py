from app import DBSession
from app.Models import Organisation

session = DBSession()


class OrganisationController(object):

    @staticmethod
    def create_org(name: str) -> None:
        """ Creates an organisation """
        org = Organisation(
            name=name
        )
        session.add(org)
        session.commit()

    @staticmethod
    def get_org_by_name(name: str) -> Organisation:
        """ Gets an organisation by name """
        return session.query(Organisation).filter(Organisation.name == name).first()

    @staticmethod
    def get_org_by_id(id: int) -> Organisation:
        """ Gets an organisation by id """
        return session.query(Organisation).filter(Organisation.id == id).first()
