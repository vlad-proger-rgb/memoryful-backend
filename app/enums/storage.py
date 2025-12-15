from enum import StrEnum


class StorageUploadIntent(StrEnum):
    AVATAR = "avatar"
    DAY_MAIN = "day_main"
    DAY_IMAGE = "day_image"
    MONTH_IMAGE = "month_image"
    WORKSPACE_ASSET = "workspace_asset"
