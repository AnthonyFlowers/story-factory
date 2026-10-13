from __future__ import annotations

import json
import os
import unittest

import helpers
from sflib import schema


def load(name):
    with open(os.path.join(helpers.STORIES, name)) as f:
        return json.load(f)


class KeywordTests(unittest.TestCase):
    def v(self, inst, sch):
        return schema.validate(inst, sch)

    def test_type(self):
        self.assertEqual(self.v("a", {"type": "string"}), [])
        self.assertEqual(self.v(1, {"type": "string"}), [": expected string"])
        self.assertEqual(self.v(None, {"type": ["string", "null"]}), [])
        self.assertTrue(self.v(True, {"type": "integer"}))  # bool is not an integer
        self.assertEqual(self.v(3, {"type": "integer"}), [])
        self.assertTrue(self.v(1.5, {"type": "integer"}))
        self.assertTrue(self.v({}, {"type": "array"}))

    def test_properties_required_additional(self):
        sch = {"type": "object", "required": ["a"], "additionalProperties": False,
               "properties": {"a": {"type": "string"}}}
        self.assertEqual(self.v({"a": "x"}, sch), [])
        self.assertEqual(self.v({}, sch), ["/a: required"])
        self.assertEqual(self.v({"a": "x", "b": 1}, sch), ["/b: additional property not allowed"])
        self.assertEqual(self.v({"a": 1}, sch), ["/a: expected string"])

    def test_enum_const(self):
        self.assertEqual(self.v("x", {"enum": ["x", "y"]}), [])
        self.assertEqual(self.v("z", {"enum": ["x", "y"]}), [': not one of ["x", "y"]'])
        self.assertEqual(self.v(None, {"enum": [None, "x"]}), [])
        self.assertEqual(self.v(1, {"const": 1}), [])
        self.assertEqual(self.v(2, {"const": 1}), [": must equal 1"])

    def test_items_minitems(self):
        sch = {"type": "array", "minItems": 2, "items": {"type": "integer"}}
        self.assertEqual(self.v([1, 2], sch), [])
        self.assertEqual(self.v([1], sch), [": at least 2 items"])
        self.assertEqual(self.v([1, "a"], sch), ["/1: expected integer"])

    def test_string_keywords(self):
        sch = {"type": "string", "minLength": 3, "maxLength": 5, "pattern": "^a"}
        self.assertEqual(self.v("abcd", sch), [])
        self.assertEqual(self.v("ab", sch), [": shorter than 3"])
        self.assertEqual(self.v("abcdef", sch), [": longer than 5"])
        self.assertEqual(self.v("bcde", sch), [": does not match ^a"])

    def test_minimum(self):
        self.assertEqual(self.v(1, {"minimum": 1}), [])
        self.assertTrue(self.v(0, {"minimum": 1}))

    def test_ref(self):
        sch = {"properties": {"a": {"$ref": "#/$defs/n"}}, "$defs": {"n": {"type": "integer"}}}
        self.assertEqual(self.v({"a": 1}, sch), [])
        self.assertEqual(self.v({"a": "x"}, sch), ["/a: expected integer"])

    def test_allof(self):
        sch = {"allOf": [{"type": "string"}, {"minLength": 3}]}
        self.assertEqual(self.v("abc", sch), [])
        self.assertEqual(self.v("a", sch), [": shorter than 3"])

    def test_if_then_silent_if(self):
        sch = {"if": {"properties": {"k": {"const": "a"}}},
               "then": {"required": ["x"]}}
        self.assertEqual(self.v({"k": "a"}, sch), ["/x: required"])
        self.assertEqual(self.v({"k": "b"}, sch), [])  # if failed silently, then not applied

    def test_unknown_keywords_ignored(self):
        self.assertEqual(self.v("a", {"$schema": "x", "$id": "y", "title": "t", "type": "string"}), [])

    def test_pointer_escaping(self):
        sch = {"additionalProperties": False}
        self.assertEqual(self.v({"a/b": 1}, sch), ["/a~1b: additional property not allowed"])


class StoryFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = schema.load_schema("story")

    def test_valid_fixtures(self):
        for name in ("story", "bug", "spike", "epic"):
            self.assertEqual(schema.validate(load(name + ".json"), self.schema), [], name)

    def test_invalid_estimate(self):
        self.assertEqual(schema.validate(load("invalid-estimate.json"), self.schema),
                         ["/story_points: additional property not allowed"])

    def test_invalid_missing_title(self):
        self.assertEqual(schema.validate(load("invalid-missing-title.json"), self.schema),
                         ["/title: required"])

    def test_invalid_bad_ac(self):
        self.assertEqual(schema.validate(load("invalid-bad-ac.json"), self.schema),
                         ["/acceptance_criteria/0/then: required"])

    def test_type_specific_requirements(self):
        s = load("story.json")
        del s["user_story"]
        self.assertIn("/user_story: required", schema.validate(s, self.schema))
        s = load("story.json")
        s["acceptance_criteria"] = s["acceptance_criteria"][:1]
        self.assertIn("/acceptance_criteria: at least 2 items", schema.validate(s, self.schema))

    def test_job_schema_bounds(self):
        js = schema.load_schema("job")
        job = {"id": "001-x", "type": "story", "mode": "new", "stage": "intake", "round": 0}
        self.assertEqual(schema.validate(job, js), [])
        self.assertTrue(schema.validate(dict(job, revisions_used=2), js))
        self.assertTrue(schema.validate(dict(job, stage="nonsense"), js))
        self.assertEqual(schema.validate(dict(job, reviews={"ac": "INVALID"}, claimed_by=None), js), [])


if __name__ == "__main__":
    unittest.main()
