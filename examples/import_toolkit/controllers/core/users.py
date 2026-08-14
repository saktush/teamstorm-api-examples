from typing import Callable, Optional, Tuple
from uuid import UUID

from teamstorm.api import TeamStormAPI
from teamstorm.models.roles import RoleModel

from import_toolkit.controllers.core.utils import normalize_str

UserCache = dict[str, Optional[Tuple[UUID, str]]]


def _find_system_user_role(roles: list[RoleModel]) -> Optional[RoleModel]:
    for role in roles:
        if role.is_system and role.name.casefold() == "user":
            return role
    return None


def _resolve_user_identifier(
    api: TeamStormAPI,
    identifier: str,
    *,
    cache: UserCache,
) -> Optional[Tuple[UUID, str]]:
    key = normalize_str(identifier)
    if not key:
        return None

    if key in cache:
        return cache[key]

    users_by_username = api.users.list(username=key)
    exact_username = [u for u in users_by_username if normalize_str(u.username) == key]
    if len(exact_username) == 1:
        resolved = (exact_username[0].id, exact_username[0].username)
        cache[key] = resolved
        return resolved

    users_by_email = api.users.list(email=key)
    exact_email = [u for u in users_by_email if normalize_str(u.email).casefold() == key.casefold()]
    if len(exact_email) == 1:
        resolved = (exact_email[0].id, exact_email[0].username)
        cache[key] = resolved
        return resolved

    users_by_display_name = api.users.list(display_name=key)
    exact_display_name = [
        u for u in users_by_display_name if normalize_str(u.display_name).casefold() == key.casefold()
    ]
    if len(exact_display_name) == 1:
        resolved = (exact_display_name[0].id, exact_display_name[0].username)
        cache[key] = resolved
        return resolved

    cache[key] = None
    return None


def _make_user_resolver(
    api: TeamStormAPI,
    *,
    user_cache: UserCache,
) -> Callable[[str], Optional[Tuple[Optional[UUID], Optional[str]]]]:
    def resolve(identifier: str) -> Optional[Tuple[Optional[UUID], Optional[str]]]:
        resolved = _resolve_user_identifier(
            api,
            identifier,
            cache=user_cache,
        )
        if resolved is None:
            return None
        return resolved[0], resolved[1]

    return resolve
