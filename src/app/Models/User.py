import binascii
import datetime
import hashlib
import os
from app import DBBase
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship


def _hash_password(password: str) -> str:
    """ Hash a password for storing. See https://www.vitoshacademy.com/hashing-passwords-in-python/"""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


class User(DBBase):
    __tablename__ = "users"

    id = Column('id', Integer(), primary_key=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    org = relationship("Organisation")
    username = Column('username', String())
    email = Column('email', String())
    first_name = Column('first_name', String())
    last_name = Column('last_name', String())
    password = Column('password', String())
    role = Column('role', Integer())
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    def __init__(
            self,
            org_id: int,
            username: str,
            email: str,
            first_name: str,
            last_name: str,
            password: str,
            role: int
    ):
        self.org_id = org_id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.password = _hash_password(password)
        self.role = role

    def check_password(self, password: str) -> bool:
        """ Checks the provided password against the stored password """
        salt = self.password[:64]
        stored_password = self.password[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha512',
                                      password.encode('utf-8'),
                                      salt.encode('ascii'),
                                      100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        return pwdhash == stored_password

    def get_jwt_secret(self):
        """ Gets the JWT secret for this users organisation """
        from app.Controllers import OrganisationController
        user_org = OrganisationController.get_org_by_id(self.org_id)
        return user_org.jwt_secret

    def get_aud(self):
        """ Gets the JWT aud for this users organisation """
        from app.Controllers import OrganisationController
        user_org = OrganisationController.get_org_by_id(self.org_id)
        return user_org.jwt_aud

    def claims(self) -> dict:
        """ Returns claims for JWT """
        return {
            "aud": self.get_aud(),
            "claims": {
                "role": self.role,
                "org": self.org_id,
                "username": self.username
            }
        }

    def as_dict(self) -> dict:
        """ Returns dict repr of User """
        return {
            "org_id": self.org_id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "password": self.password,
            "role": self.role
        }
