# common settings
_jwt_secret = '6A&706zF9KyjFu7Y$h6WfG6O^X$vL6dRM7QnXGba&ThdE8L7Kc3^zo!j5'


class Local(object):
    JWT_SECRET = _jwt_secret
    DB_USER = "etemt"
    DB_PASS = "etemt"
    DB_HOST = "localhost"


class Staging(object):
    JWT_SECRET = _jwt_secret
