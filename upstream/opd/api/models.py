"""Pydantic v2 response models for the proposed OpenParlData topic resources (topics.md). FastAPI-ready; no other deps.

The nested language format (`lang_format=nested`, OPD's default) returns `label: {"de", "fr", "it", "rm"}`;
`lang_format=flat&lang=fr` returns `label: "…"`. Evidence is one object in the API and flat `evidence_*` columns in the
table and the CSV/Excel output, as OPD flattens other relations."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

Lane = Literal["readings_agree", "please_check"]
Status = Literal["suggested", "confirmed", "rejected"]
Provenance = Literal["inferred", "confirmed"]


class Labels(BaseModel):
    de: Optional[str] = None
    fr: Optional[str] = None
    it: Optional[str] = None
    rm: Optional[str] = None


class Evidence(BaseModel):
    """One sentence of the affair that supports the topic; `quote` is an exact substring of that field."""
    field: Literal["title", "title_long", "text", "doc"]
    text_id: Optional[int] = Field(None, description="texts.id when the sentence comes from a text")
    doc_id: Optional[int] = Field(None, description="docs.id when it comes from a document")
    char_start: int
    char_end: int
    quote: str


class Provenance_(BaseModel):
    """What produced a machine row; enough to trace and reproduce it."""
    model: Optional[str] = Field(None, description="served model name")
    model_build: Optional[str] = Field(None, description="served build (system_fingerprint)")
    cutoffs_id: Optional[str] = None
    prompt_id: Optional[str] = Field(None, description="sha256[:12] of each exact prompt, comma-separated")
    input_hash: Optional[str] = None
    engine_version: Optional[str] = None


class Topic(BaseModel):
    id: int
    affair_id: int
    body_id: Optional[int] = None
    body_key: Optional[str] = None
    scheme_id: int
    scheme_key: str = Field(..., examples=["aps", "adhoc/digitalisierung", "be-directorates"])
    level: Literal[1, 2] = Field(..., description="1 = chapter or yes/no, 2 = subtopic")
    code: str = Field(..., examples=["aps:1.7.2.", "aps:kw:1374918", "adhoc/digitalisierung:yes"])
    parent_code: Optional[str] = None
    rank: int = Field(..., ge=1, description="1 = the label; 2-3 = ranked suggestions")
    label: Union[Labels, str, None] = None
    p: Optional[float] = Field(None, ge=0, le=1, description="recalibrated probability (per served build)")
    p_raw: Optional[float] = Field(None, ge=0, le=1, description="model probability before recalibration")
    lane: Optional[Lane] = None
    status: Status
    provenance: Provenance = Field(..., description="inferred = machine suggestion; confirmed = a published decision")
    evidence: Optional[Evidence] = None
    generated_by: Optional[Provenance_] = None
    valid_from: datetime
    valid_to: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    confirmed_by_body_id: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TopicScheme(BaseModel):
    id: int
    scheme_key: str
    version: str
    type: Literal["standard", "body", "adhoc"]
    levels: Literal[1, 2]
    name: Union[Labels, str, None] = None
    question: Union[Labels, str, None] = None
    body_id: Optional[int] = None
    body_key: Optional[str] = None
    licence: Optional[str] = Field(None, description="SPDX id of codes and labels; null = to be agreed with the source")
    source_name: str
    source_url: Optional[str] = None
    notes: Optional[str] = None
    code_count: Optional[int] = None
    active: bool
    created_at: datetime
    updated_at: datetime


class TopicCode(BaseModel):
    id: int
    scheme_id: int
    scheme_key: str
    code: str
    level: Literal[1, 2]
    parent_code: Optional[str] = None
    position: int
    external_id: Optional[str] = None
    label: Union[Labels, str, None] = None


class Meta(BaseModel):
    """OPD's pagination block, unchanged."""
    offset: int
    limit: int
    total_records: int
    total_pages: int
    current_page: int
    has_more: bool
    next_page: Optional[str] = None
    prev_page: Optional[str] = None
    first_page: Optional[str] = None
    last_page: Optional[str] = None
    self: Optional[str] = None


class TopicList(BaseModel):
    data: list[Topic]
    meta: Meta


class TopicSchemeList(BaseModel):
    data: list[TopicScheme]
    meta: Meta


class TopicCodeList(BaseModel):
    data: list[TopicCode]
    meta: Meta
