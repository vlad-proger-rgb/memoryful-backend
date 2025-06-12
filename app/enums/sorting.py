from enum import StrEnum


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class DaySortField(StrEnum):
    TIMESTAMP = "timestamp"
    STEPS = "steps"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
