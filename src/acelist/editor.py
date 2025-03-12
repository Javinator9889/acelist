from __future__ import annotations

from collections import namedtuple
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

if TYPE_CHECKING:
    from m3u8 import M3U8
    from urllib.parse import ParseResult


AceId = namedtuple("AceId", ["id", "value"])


def _get_id(uri: ParseResult) -> AceId:
    q = parse_qs(uri.query)
    if "id" in q:
        return AceId("id", q["id"][0])
    return AceId("infohash", q["infohash"][0])


def modify_m3u8_uri(
    playlist: M3U8,
    unique_id: bool = True,
    new_scheme: str = "http",
    new_host: str = "localhost",
    new_port: int = 6878,
) -> M3U8:
    for seg in playlist.segments:
        if not seg.uri:
            continue
        uri_id = _get_id(urlparse(seg.uri))
        seg.uri = f"{new_scheme}://{new_host}:{new_port}/ace/getstream?{uri_id.id}={uri_id.value}"
        if unique_id:
            uid = uuid4()
            seg.uri += f"&pid={uid}"
    return playlist
