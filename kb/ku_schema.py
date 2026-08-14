# -*- coding: utf-8 -*-
"""
Knowledge Unit (KU) schema definition and validation.
Version: ku/1.0  (matches the "schema" field in kb/master_judged.json)
validate(k) returns a list of error strings; empty list means compliant.

type enum is taken from the actual values used by the existing 471 KUs:
  parameter / requirement / test_method / classification / procedure /
  non_exam / sample_prep / criterion / definition / formula
KU may carry extension fields (product_std / test_std / scope / syllabus_ref)
for structured knowledge mapping; validate() ignores unknown fields.
"""
SCHEMA_VERSION = "ku/1.0"

REQUIRED = ["standard_no", "type", "title", "clause",
            "is_exam_point", "priority", "key_requirements",
            "interpretation", "doc_id"]

TYPES = {
    "parameter", "requirement", "test_method", "classification",
    "procedure", "non_exam", "sample_prep", "criterion", "definition", "formula",
}

PRIORITIES = {"P0", "P1", "P2", "NA"}


def validate(k):
    """Return a list of error strings; empty list means compliant."""
    if not isinstance(k, dict):
        return ["KU is not an object"]
    errs = []
    for f in REQUIRED:
        if f not in k:
            errs.append("missing field %s" % f)
    t = k.get("type")
    if t not in TYPES:
        errs.append("type invalid: %r" % (t,))
    p = k.get("priority")
    if p not in PRIORITIES:
        errs.append("priority invalid: %r" % (p,))
    if k.get("is_exam_point") is True and not k.get("key_requirements"):
        errs.append("exam-point KU missing key_requirements")
    if not isinstance(k.get("key_requirements"), list):
        errs.append("key_requirements should be a list")
    return errs


def is_valid(k):
    return not validate(k)
