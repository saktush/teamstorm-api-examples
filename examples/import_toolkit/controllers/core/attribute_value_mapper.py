from __future__ import annotations

import re
from datetime import timezone
from typing import Callable, Optional
from uuid import UUID

from dateutil.parser import isoparse

from teamstorm.models.enums import AttributeType
from teamstorm.models.workitems_attributes_create import (
    CreateDateFieldRequestBody,
    CreateNumberFieldRequestBody,
    CreateTagFieldRequestBody,
    CreateTimeFieldRequestBody,
    CreateUniSelectFieldRequestBody,
    CreateUniStringFieldRequestBody,
    CreateUserFieldRequestBody,
    CreateUserFieldValueModel,
    CreateWorkitemAttributeRequestBody,
)
from teamstorm.models.workitems_attributes_update import (
    UpdateDateFieldRequestBody,
    UpdateNumberFieldRequestBody,
    UpdateTagFieldRequestBody,
    UpdateTimeFieldRequestBody,
    UpdateUniSelectFieldRequestBody,
    UpdateUniStringFieldRequestBody,
    UpdateUserFieldRequestBody,
    UpdateUserFieldValueModel,
    UpdateWorkitemAttributeRequestBody,
)

OptionResolver = Callable[[str], Optional[str]]
UserResolver = Callable[[str], Optional[tuple[Optional[UUID], Optional[str]]]]
WarningSink = Callable[[str], None]

_TIME_UNITS: dict[str, int] = {
    "": 1,
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
}


def _normalize_string(raw_value: object) -> str:
    return str(raw_value).strip()


def normalize_attribute_cell(
    attribute_type: AttributeType,
    raw_value: object,
) -> object | None:
    normalized = _normalize_string(raw_value)
    if not normalized:
        return None

    if attribute_type == AttributeType.UniString:
        return normalized

    if attribute_type == AttributeType.Number:
        number_text = normalized.replace(",", ".")
        return float(number_text)

    if attribute_type == AttributeType.Date:
        parsed = isoparse(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    if attribute_type == AttributeType.UniSelect:
        return normalized

    if attribute_type == AttributeType.Tag:
        parts = re.split(r"[;,]", normalized)
        seen: set[str] = set()
        values: list[str] = []
        for part in parts:
            value = part.strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            values.append(value)
        return values or None

    if attribute_type == AttributeType.User:
        return normalized

    if attribute_type == AttributeType.TimeDuration:
        match = re.fullmatch(
            r"\s*(?P<number>-?\d+(?:[.,]\d+)?)\s*(?P<unit>[A-Za-z]*)\s*",
            normalized,
        )
        if match is None:
            raise ValueError(f"Invalid duration value: {normalized!r}")

        value = float(match.group("number").replace(",", "."))
        unit = match.group("unit").lower()
        if unit not in _TIME_UNITS:
            raise ValueError(f"Unknown duration unit: {unit!r}")
        return int(round(value * _TIME_UNITS[unit]))

    raise ValueError(f"Unsupported attribute type: {attribute_type!r}")


def build_create_attribute_value(
    *,
    attribute_id: UUID,
    attribute_type: AttributeType,
    raw_value: object,
    resolve_option_id: OptionResolver | None = None,
    resolve_user: UserResolver | None = None,
    warn: WarningSink | None = None,
) -> CreateWorkitemAttributeRequestBody | None:
    normalized = normalize_attribute_cell(attribute_type, raw_value)
    if normalized is None:
        return None

    if attribute_type == AttributeType.UniString:
        return CreateUniStringFieldRequestBody(
            id=attribute_id,
            type=AttributeType.UniString,
            value=str(normalized),
        )

    if attribute_type == AttributeType.Number:
        return CreateNumberFieldRequestBody(
            id=attribute_id,
            type=AttributeType.Number,
            value=float(normalized),
        )

    if attribute_type == AttributeType.Date:
        return CreateDateFieldRequestBody(
            id=attribute_id,
            type=AttributeType.Date,
            value=normalized,
        )

    if attribute_type == AttributeType.UniSelect:
        if resolve_option_id is None:
            raise ValueError("resolve_option_id is required for UniSelect attributes")
        option_id = resolve_option_id(str(normalized))
        if option_id is None:
            if warn is not None:
                warn(f"Cannot resolve option {normalized!r}")
            return None
        return CreateUniSelectFieldRequestBody(
            id=attribute_id,
            type=AttributeType.UniSelect,
            value=option_id,
        )

    if attribute_type == AttributeType.Tag:
        if resolve_option_id is None:
            raise ValueError("resolve_option_id is required for Tag attributes")
        tag_ids: list[str] = []
        for tag_name in normalized:
            tag_id = resolve_option_id(tag_name)
            if tag_id is None:
                if warn is not None:
                    warn(f"Cannot resolve tag option {tag_name!r}")
                continue
            tag_ids.append(tag_id)
        if not tag_ids:
            return None
        return CreateTagFieldRequestBody(
            id=attribute_id,
            type=AttributeType.Tag,
            value=tag_ids,
        )

    if attribute_type == AttributeType.User:
        if resolve_user is None:
            raise ValueError("resolve_user is required for User attributes")
        resolved = resolve_user(str(normalized))
        if resolved is None:
            if warn is not None:
                warn(f"Cannot resolve user {normalized!r}")
            return None
        user_id, user_name = resolved
        return CreateUserFieldRequestBody(
            id=attribute_id,
            type=AttributeType.User,
            value=CreateUserFieldValueModel(id=user_id, userName=user_name),
        )

    if attribute_type == AttributeType.TimeDuration:
        return CreateTimeFieldRequestBody(
            id=attribute_id,
            type=AttributeType.TimeDuration,
            value=int(normalized),
        )

    raise ValueError(f"Unsupported attribute type: {attribute_type!r}")


def build_update_attribute_value(
    *,
    attribute_type: AttributeType,
    raw_value: object,
    resolve_option_id: OptionResolver | None = None,
    resolve_user: UserResolver | None = None,
    warn: WarningSink | None = None,
) -> UpdateWorkitemAttributeRequestBody | None:
    normalized = normalize_attribute_cell(attribute_type, raw_value)
    if normalized is None:
        return None

    if attribute_type == AttributeType.UniString:
        return UpdateUniStringFieldRequestBody(
            type=AttributeType.UniString,
            value=str(normalized),
        )

    if attribute_type == AttributeType.Number:
        return UpdateNumberFieldRequestBody(
            type=AttributeType.Number,
            value=float(normalized),
        )

    if attribute_type == AttributeType.Date:
        return UpdateDateFieldRequestBody(
            type=AttributeType.Date,
            value=normalized,
        )

    if attribute_type == AttributeType.UniSelect:
        if resolve_option_id is None:
            raise ValueError("resolve_option_id is required for UniSelect attributes")
        option_id = resolve_option_id(str(normalized))
        if option_id is None:
            if warn is not None:
                warn(f"Cannot resolve option {normalized!r}")
            return None
        return UpdateUniSelectFieldRequestBody(
            type=AttributeType.UniSelect,
            value=option_id,
        )

    if attribute_type == AttributeType.Tag:
        if resolve_option_id is None:
            raise ValueError("resolve_option_id is required for Tag attributes")
        tag_ids: list[str] = []
        for tag_name in normalized:
            tag_id = resolve_option_id(tag_name)
            if tag_id is None:
                if warn is not None:
                    warn(f"Cannot resolve tag option {tag_name!r}")
                continue
            tag_ids.append(tag_id)
        if not tag_ids:
            return None
        return UpdateTagFieldRequestBody(
            type=AttributeType.Tag,
            value=tag_ids,
        )

    if attribute_type == AttributeType.User:
        if resolve_user is None:
            raise ValueError("resolve_user is required for User attributes")
        resolved = resolve_user(str(normalized))
        if resolved is None:
            if warn is not None:
                warn(f"Cannot resolve user {normalized!r}")
            return None
        user_id, user_name = resolved
        return UpdateUserFieldRequestBody(
            type=AttributeType.User,
            value=UpdateUserFieldValueModel(id=user_id, userName=user_name),
        )

    if attribute_type == AttributeType.TimeDuration:
        return UpdateTimeFieldRequestBody(
            type=AttributeType.TimeDuration,
            value=int(normalized),
        )

    raise ValueError(f"Unsupported attribute type: {attribute_type!r}")
