"""Pydantic models for every file format in spec/05. They are the source of truth.

`CONTRACTS` maps each contract's name to its model; `json_schema` renders the schema
that `make schemas` writes to `schemas/<name>.schema.json`.
"""

from __future__ import annotations

from typing import Any

from accel_core.contracts._base import SCHEMA_VERSION, Contract
from accel_core.contracts.evals import EvalCase, EvalReport
from accel_core.contracts.finding import (
    Finding,
    RuntimeEvidence,
    StaticEvidence,
    check_static_evidence,
)
from accel_core.contracts.gate import GateRecord
from accel_core.contracts.knowledge import ExtractPlan, KnowledgeManifest
from accel_core.contracts.playbook import Playbook
from accel_core.contracts.project import Project
from accel_core.contracts.setup import InstallCheck, VersionsLock
from accel_core.contracts.skills import CatalogEntry, Provenance, SkillsLock
from accel_core.contracts.task import Task
from accel_core.contracts.ui_spec import UiSpec

CONTRACTS: dict[str, type[Contract]] = {
    "finding": Finding,
    "playbook": Playbook,
    "catalog-entry": CatalogEntry,
    "knowledge-manifest": KnowledgeManifest,
    "extract-plan": ExtractPlan,
    "install-check": InstallCheck,
    "versions-lock": VersionsLock,
    "skills-lock": SkillsLock,
    "provenance": Provenance,
    "eval-case": EvalCase,
    "eval-report": EvalReport,
    "ui-spec": UiSpec,
    "project": Project,
    "task": Task,
    "gate-record": GateRecord,
}

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def json_schema(name: str) -> dict[str, Any]:
    """Return the JSON Schema for the contract called `name`."""
    schema = CONTRACTS[name].model_json_schema(mode="validation")
    return {"$schema": JSON_SCHEMA_DIALECT, "$id": f"{name}.schema.json", **schema}


__all__ = [
    "CONTRACTS",
    "SCHEMA_VERSION",
    "CatalogEntry",
    "Contract",
    "EvalCase",
    "EvalReport",
    "ExtractPlan",
    "Finding",
    "GateRecord",
    "InstallCheck",
    "KnowledgeManifest",
    "Playbook",
    "Project",
    "Provenance",
    "RuntimeEvidence",
    "SkillsLock",
    "StaticEvidence",
    "Task",
    "UiSpec",
    "VersionsLock",
    "check_static_evidence",
    "json_schema",
]
