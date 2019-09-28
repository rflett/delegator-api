from flask_restplus import fields


class NullableDateTime(fields.DateTime):
    __schema_type__ = ['datetime', 'null']
    __schema_example__ = 'None|2019-09-17T19:08:00+10:00'


class NullableInteger(fields.Integer):
    __schema_type__ = ['integer', 'null']
    __schema_example__ = 'None|int'
