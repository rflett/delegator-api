from app import DBSession
from app.Models import Organisation

session = DBSession()


class OrganisationController(object):
    @staticmethod
    def get_org_by_id(id: int) -> Organisation:
        """ 
        Gets an organisation by its id.
        
        :param id int: The id of the organisation

        :return: The Organisation object.
        """
        return session.query(Organisation).filter(Organisation.id == id).first()
