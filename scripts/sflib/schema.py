"""A small JSON Schema subset validator (stdlib only)."""
from __future__ import annotations

import json
import os
import re

from . import SFError


def load_schema(name: str) -> dict:
    """Load schemas/<name>.schema.json from the repo."""
    from . import config
    path = os.path.join(config.root(), "schemas", name + ".schema.json")
    with open(path) as f:
        return json.load(f)


def _is_type(value, t: str) -> bool:
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def _esc(key) -> str:
    return str(key).replace("~", "~0").replace("/", "~1")


def _resolve(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        raise SFError("unsupported $ref %s" % ref, 2)
    node = root
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _validate(inst, schema: dict, root: dict, ptr: str, errs: list) -> None:
    if "$ref" in schema:
        _validate(inst, _resolve(schema["$ref"], root), root, ptr, errs)
    if "allOf" in schema:
        for sub in schema["allOf"]:
            _validate(inst, sub, root, ptr, errs)
    if "if" in schema:
        probe: list = []
        _validate(inst, schema["if"], root, ptr, probe)
        if not probe and "then" in schema:
            _validate(inst, schema["then"], root, ptr, errs)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(inst, t) for t in types):
            errs.append("%s: expected %s" % (ptr, " or ".join(types)))
            return
    if "const" in schema and not (inst == schema["const"] and type(inst) is type(schema["const"])):
        errs.append("%s: must equal %s" % (ptr, json.dumps(schema["const"])))
    if "enum" in schema:
        if not any(inst == v and type(inst) is type(v) for v in schema["enum"]):
            errs.append("%s: not one of %s" % (ptr, json.dumps(schema["enum"])))
    if isinstance(inst, str):
        if "minLength" in schema and len(inst) < schema["minLength"]:
            errs.append("%s: shorter than %d" % (ptr, schema["minLength"]))
        if "maxLength" in schema and len(inst) > schema["maxLength"]:
            errs.append("%s: longer than %d" % (ptr, schema["maxLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errs.append("%s: does not match %s" % (ptr, schema["pattern"]))
    if _is_type(inst, "number"):
        if "minimum" in schema and inst < schema["minimum"]:
            errs.append("%s: less than minimum %s" % (ptr, schema["minimum"]))
        if "maximum" in schema and inst > schema["maximum"]:
            errs.append("%s: greater than maximum %s" % (ptr, schema["maximum"]))
    if isinstance(inst, dict):
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in inst:
                errs.append("%s/%s: required" % (ptr, _esc(name)))
        addl = schema.get("additionalProperties")
        for key, val in inst.items():
            if key in props:
                _validate(val, props[key], root, "%s/%s" % (ptr, _esc(key)), errs)
            elif addl is False:
                errs.append("%s/%s: additional property not allowed" % (ptr, _esc(key)))
            elif isinstance(addl, dict):
                _validate(val, addl, root, "%s/%s" % (ptr, _esc(key)), errs)
    if isinstance(inst, list):
        if "minItems" in schema and len(inst) < schema["minItems"]:
            errs.append("%s: at least %d items" % (ptr, schema["minItems"]))
        if "items" in schema:
            for i, item in enumerate(inst):
                _validate(item, schema["items"], root, "%s/%d" % (ptr, i), errs)


def validate(instance, schema: dict) -> list:
    """Return a list of "<json-pointer>: <message>" strings ("" pointer = root)."""
    errs: list = []
    _validate(instance, schema, schema, "", errs)
    return errs
