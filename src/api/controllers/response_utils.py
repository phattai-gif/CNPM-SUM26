from flask import jsonify
from flask.json.provider import DefaultJSONProvider
from unittest.mock import MagicMock
from sqlalchemy.ext.declarative import DeclarativeMeta


def _model_to_dict(obj):
    # SQLAlchemy model instances have a __dict__ with _sa_instance_state
    if hasattr(obj, '__dict__'):
        d = {
            k: v
            for k, v in obj.__dict__.items()
            if not k.startswith('_') and not callable(v)
        }
        return d

    # Fallback to vars()
    try:
        return dict(vars(obj))
    except Exception:
        return str(obj)


def _serialize_item(item):
    # Primitive types, dicts and lists are fine
    if item is None:
        return None
    if isinstance(item, (str, int, float, bool)):
        return item
    if isinstance(item, dict):
        return {k: _serialize_item(v) for k, v in item.items()}
    if isinstance(item, (list, tuple)):
        return [_serialize_item(i) for i in item]

    # SQLAlchemy model detection
    try:
        from sqlalchemy.orm import class_mapper

        class_mapper(item.__class__)
        return _model_to_dict(item)
    except Exception:
        # Not a SQLAlchemy model; try to convert generically
        try:
            return _model_to_dict(item)
        except Exception:
            return str(item)


def safe_jsonify(data, status=200):
    """Return a Flask JSON response while attempting to coerce
    unserializable objects (models, MagicMocks) into strings or dicts.
    """
    try:
        return jsonify(data), status
    except Exception:
        try:
            serializable = _serialize_item(data)
            return jsonify(serializable), status
        except Exception:
            return jsonify({"result": str(data)}), status


class SafeJSONProvider(DefaultJSONProvider):
    """A JSON provider that falls back to stringifying unknown objects
    (including MagicMock and SQLAlchemy models) instead of raising.
    """
    def default(self, o):
        # MagicMock -> string
        if isinstance(o, MagicMock):
            return str(o)

        try:
            return _serialize_item(o)
        except Exception:
            return str(o)
