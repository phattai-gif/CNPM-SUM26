from marshmallow import Schema, fields, validate


class CriteriaSchema(Schema):
    id = fields.Int(dump_only=True)
    round_id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    max_score = fields.Float(load_default=10.0, dump_default=10.0)
    weight = fields.Float(load_default=1.0, dump_default=1.0)
    created_at = fields.Str(dump_only=True)


class RoundSchema(Schema):
    id = fields.Int(dump_only=True)
    contest_id = fields.Int(dump_only=True)
    round_number = fields.Int(load_default=1)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    start_date = fields.Str(allow_none=True)
    end_date = fields.Str(allow_none=True)
    weight = fields.Float(load_default=1.0, dump_default=1.0)
    status = fields.Str(load_default='upcoming', validate=validate.OneOf(['upcoming', 'ongoing', 'completed']))
    created_at = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)
    criteria = fields.List(fields.Nested(CriteriaSchema), load_default=[])


class ContestCreateRequestSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    slug = fields.Str(allow_none=True, validate=validate.Length(max=255))
    description = fields.Str(allow_none=True)
    rules = fields.Str(allow_none=True)
    banner_url = fields.Str(allow_none=True, validate=validate.Length(max=512))
    status = fields.Str(load_default='draft', validate=validate.OneOf(['draft', 'published', 'active', 'completed', 'archived']))
    start_date = fields.Str(allow_none=True)
    end_date = fields.Str(allow_none=True)


class ContestUpdateRequestSchema(Schema):
    title = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    rules = fields.Str(allow_none=True)
    banner_url = fields.Str(allow_none=True, validate=validate.Length(max=512))
    status = fields.Str(validate=validate.OneOf(['draft', 'published', 'active', 'completed', 'archived']))
    start_date = fields.Str(allow_none=True)
    end_date = fields.Str(allow_none=True)


class ContestRulesUpdateRequestSchema(Schema):
    rules = fields.Str(required=True)


class ContestConfigurationRequestSchema(Schema):
    rules = fields.Str(allow_none=True)
    rounds = fields.List(fields.Nested(RoundSchema), allow_none=True)


class ContestResponseSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    slug = fields.Str()
    description = fields.Str(allow_none=True)
    rules = fields.Str(allow_none=True)
    banner_url = fields.Str(allow_none=True)
    created_by = fields.Int()
    status = fields.Str()
    start_date = fields.Str(allow_none=True)
    end_date = fields.Str(allow_none=True)
    created_at = fields.Str(allow_none=True)
    updated_at = fields.Str(allow_none=True)
    rounds = fields.List(fields.Nested(RoundSchema))
