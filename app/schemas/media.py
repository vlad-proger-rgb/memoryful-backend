from fastapi_camelcase import CamelModel


class ResolvedBackground(CamelModel):
    """A stored background, resolved to a URL the browser can fetch directly.

    Shared by workspace pages and months so both read the same shape.
    """

    key: str | None = None
    url: str | None = None
    is_video: bool = False
    #: ~32px WebP `data:` URI, painted blurred while the real media loads.
    placeholder: str | None = None
