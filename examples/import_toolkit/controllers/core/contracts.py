import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta, timezone
from typing import Optional
from uuid import UUID

from teamstorm.models.enums import AttributeType

TZ_MSK = timezone(timedelta(hours=3))
SELECT_TAG_WRITE_STRATEGY = "id-first+name-retry-on-mismatch,readback-verify"

_TYPE_MARKER_RE = re.compile(r"^(?P<name>.*?)\[(?P<type>[^\]]+)\]\s*$")
_TYPE_ALIASES: dict[str, AttributeType] = {
    "unistring": AttributeType.UniString,
    "string": AttributeType.UniString,
    "text": AttributeType.UniString,
    "number": AttributeType.Number,
    "num": AttributeType.Number,
    "int": AttributeType.Number,
    "float": AttributeType.Number,
    "date": AttributeType.Date,
    "datetime": AttributeType.Date,
    "uniselect": AttributeType.UniSelect,
    "select": AttributeType.UniSelect,
    "tag": AttributeType.Tag,
    "tags": AttributeType.Tag,
    "user": AttributeType.User,
    "time": AttributeType.TimeDuration,
    "timeduration": AttributeType.TimeDuration,
    "duration": AttributeType.TimeDuration,
}


@dataclass
class Counters:
    sprints_created: int = 0
    sprints_patched: int = 0
    workitems_created: int = 0
    workitems_patched: int = 0
    custom_attr_updates_attempted: int = 0
    custom_attr_updates_succeeded: int = 0
    custom_attr_updates_failed: int = 0
    custom_attr_updates_skipped: int = 0
    rows_skipped: int = 0


@dataclass(frozen=True)
class CustomAttributeSpec:
    source_column: str
    attribute_name: str
    requested_type: AttributeType
    unknown_marker: bool


@dataclass
class SyncedAttribute:
    spec: CustomAttributeSpec
    resolved_type: AttributeType
    attribute_id: Optional[UUID]
    options_by_name: dict[str, UUID]


@dataclass
class SyncContext:
    attributes_by_column: dict[str, SyncedAttribute]
    user_cache: dict[str, Optional[tuple[UUID, str]]]
    known_types: set[str]


@dataclass(frozen=True)
class PendingCustomAttributeUpdate:
    source_column: str
    raw_value: str
    synced_attr: SyncedAttribute
    payload: object


def default_dict_set() -> defaultdict:
    return defaultdict(set)
