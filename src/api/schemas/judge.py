from marshmallow import Schema, fields, validate, ValidationError, validates_schema


class AssignJudgeRequestSchema(Schema):
    judge_id = fields.Int(allow_none=True)
    judge_ids = fields.List(fields.Int(), allow_none=True)
    submission_id = fields.Int(allow_none=True)
    status = fields.Str(load_default='assigned', validate=validate.OneOf(['assigned', 'grading', 'completed']))

    @validates_schema
    def validate_judge_fields(self, data, **kwargs):
        if not data.get('judge_id') and not data.get('judge_ids'):
            raise ValidationError("Cần truyền judge_id hoặc danh sách judge_ids.", field_name="judge_id")


class JudgeAssignmentResponseSchema(Schema):
    id = fields.Int()
    round_id = fields.Int()
    submission_id = fields.Int(allow_none=True)
    judge_id = fields.Int()
    status = fields.Str()
    assigned_at = fields.Str(allow_none=True)
    judge_name = fields.Str(allow_none=True)
    judge_email = fields.Str(allow_none=True)
    judge_username = fields.Str(allow_none=True)
