from marshmallow import Schema, fields, validate

VALID_ROLES = ['admin', 'organizer', 'participant', 'judge']


class RegisterUserRequestSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6))
    passwordconfirm = fields.Str(required=True)
    email = fields.Email(required=True)
    full_name = fields.Str(required=False, allow_none=True)
    role = fields.Str(
        required=False,
        load_default='participant',
        validate=validate.OneOf(VALID_ROLES, error="Role must be one of: admin, organizer, participant, judge")
    )


class RegisterUserResponseSchema(Schema):
    id = fields.Int()
    username = fields.Str()
    email = fields.Email()
    full_name = fields.Str()
    role = fields.Str()


class LoginUserRequestSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class LoginUserResponseSchema(Schema):
    id = fields.Int()
    username = fields.Str()
    email = fields.Email()
    full_name = fields.Str()
    role = fields.Str()
    token = fields.Str()


# Aliases for backward compatibility
RigisterUserRequestSchema = RegisterUserRequestSchema
RigisterUserResponseSchema = RegisterUserResponseSchema
