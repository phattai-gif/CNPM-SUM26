from marshmallow import Schema, fields, validate


class AdminRoleUpdateSchema(Schema):
    role = fields.Str(required=True, validate=validate.OneOf(
        ['admin', 'organizer', 'participant', 'judge']
    ))


class AdminStatusUpdateSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(['active', 'locked']))