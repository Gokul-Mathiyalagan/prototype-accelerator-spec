"""Map identity-provider groups to app roles."""

ROLE_MAPPING = {
    "ti-analysts": "analyst",
    "ti-viewers": "viewer",
    "ti-admins": "admin",
}

ROLE_RANK = {"viewer": 1, "analyst": 2, "admin": 3}


def roles_for_groups(groups: list[str]) -> set[str]:
    return {ROLE_MAPPING[group] for group in groups if group in ROLE_MAPPING}


def has_role(roles: set[str], required: str) -> bool:
    return any(ROLE_RANK[role] >= ROLE_RANK[required] for role in roles)
