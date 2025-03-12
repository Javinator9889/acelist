"""Matcher module. Links a M3U8 playlist with an XMLTV file."""

from __future__ import annotations

from asyncio import Lock, Condition, Event
from copy import copy
from datetime import datetime, UTC
from enum import StrEnum
from lxml.etree import XMLParser, fromstring
from m3u8 import M3U8, protocol
from m3u8.parser import save_segment_custom_value
from typing import TYPE_CHECKING

import difflib
import logging
import m3u8
import re

if TYPE_CHECKING:
    from lxml.etree import Element
    from typing import Callable

    save_segment_custom_value: Callable[[dict, str, dict], None]


class StateAttrs(StrEnum):
    SEGMENT = "segment"
    SEGMENT_TITLE = "title"
    SEGMENT_DURATION = "duration"
    EXTINF = "extinf_props"
    EXPECT_SEGMENT = "expect_segment"


def parse_iptv_attributes(line: str, lineno: int, data: dict, state: dict) -> bool:
    """Parses the custom attributes usually shipped with #EXTINF tags.

    Args:
        line (:obj:`str`): The line to parse.
        lineno (:obj:`int`): The line number
        data (:obj:`dict`): The data dictionary
        state (:obj:`dict`): The state dictionary

    Returns:
        bool: :obj:`True` if the line was parsed successfully, :obj:`False` otherwise.
    """
    if not line.startswith(protocol.extinf):
        return False

    title = ""
    chunks = line.replace(f"{protocol.extinf}:", "").split(",", 1)
    match len(chunks):
        case 2:
            duration_and_props, title = chunks
        case 1:
            duration_and_props = chunks[0]
        case _:
            return False

    additional_props = {}
    chunks = duration_and_props.strip().split(" ", 1)
    match len(chunks):
        case 2:
            duration, raw_props = chunks
            matched_props = re.finditer(r'([\w\-]+)="([^"]*)"', raw_props)
            for match in matched_props:
                additional_props[match.group(1)] = match.group(2)
        case _:
            duration = duration_and_props

    if StateAttrs.SEGMENT not in state:
        state[StateAttrs.SEGMENT] = {}
    state[StateAttrs.SEGMENT][StateAttrs.SEGMENT_DURATION] = float(duration)
    state[StateAttrs.SEGMENT][StateAttrs.SEGMENT_TITLE] = title

    # Helper function for saving custom values
    save_segment_custom_value(state, StateAttrs.EXTINF, additional_props)

    # Tell 'main parser' that we expect an URL on next lines
    state[StateAttrs.EXPECT_SEGMENT] = True

    # Tell 'main parser' that it can go to next line, we've parsed current fully.
    return True


def dumps(iptv: M3U8) -> str:
    """Dumps the M3U8 object into a string.

    Args:
        iptv (:obj:`M3U8`): The M3U8 object to dump.

    Returns:
        str: The dumped M3U8 object.
    """
    output = ["#EXTM3U"]
    for seg in iptv.segments:
        segdumps = []
        seg_props = seg.custom_parser_values[StateAttrs.EXTINF]
        if seg.uri and "tvg-id" in seg_props:
            if seg.duration is not None:
                segdumps.append(f"#EXTINF:{int(seg.duration)}")
                if "tvg-id" in seg_props:
                    segdumps.append(f' tvg-id="{seg_props["tvg-id"]}"')
                if seg.title:
                    segdumps.append(f",{seg.title}")
                segdumps.append("\n")
            segdumps.append(seg.uri)
        if segdumps:
            output.append("".join(segdumps))
    return "\n".join(output)


class Matcher:
    def __init__(self) -> None:
        self._playlist: M3U8 | None = None
        self._playlist_changed: bool = False
        self._cached_playlist: int = 0
        self._channels: Element | None = None
        self._channels_changed: bool = False
        self._cached_channels: int = 0
        self._processed_playlist: M3U8 | None = None
        self._parser = XMLParser(recover=True)

        self._lock = Lock()
        self._cond = Condition()
        self._processing_done = Event()
        self._first = True

    async def get_playlist(self) -> M3U8 | None:
        async with self._lock:
            if self._playlist_changed:
                self._playlist_changed = False

            return self._playlist

    async def set_playlist(self, content: str) -> None:
        logging.debug("Setting playlist")
        async with self._lock:
            if hash(content) == self._cached_playlist:
                return
            self._cached_playlist = hash(content)
            playlist = m3u8.loads(content, custom_tags_parser=parse_iptv_attributes)
            logging.debug("loaded playlist %s (%d)", playlist, self._cached_playlist)
            logging.debug("Detected playlist change")
            self._playlist = playlist
            self._playlist_changed = True
            async with self._cond:
                logging.debug("playlist notifying")
                self._cond.notify_all()

    async def get_channels(self) -> Element | None:
        async with self._lock:
            if self._channels_changed:
                self._channels_changed = False

            return self._channels

    async def set_channels(self, content: bytes) -> None:
        logging.debug("Setting channels")
        async with self._lock:
            if hash(content) == self._cached_channels:
                return
            self._cached_channels = hash(content)
            logging.debug("parsing channels, parser: %s", self._parser)
            channels = fromstring(content, self._parser)
            logging.debug("loaded channels %s (%d)", channels, self._cached_channels)
            logging.debug("Detected channels change")
            self._channels = channels
            self._channels_changed = True
            async with self._cond:
                logging.debug("channels notifying")
                self._cond.notify_all()

    @property
    async def ready(self) -> bool:
        await self._processing_done.wait()

    async def get_processed_playlist(self) -> M3U8:
        await self.ready
        async with self._lock:
            return self._processed_playlist

    def _should_process_segments(self) -> bool:
        if self._first:
            return self._channels_changed and self._playlist_changed
        return self._playlist_changed or self._channels_changed

    async def update_segments(
        self, cleanup_title: list[re.Pattern], cutoff: float = 0.95
    ) -> None:
        logging.debug("Updating segments")
        wait_start = datetime.now(tz=UTC)
        async with self._lock:
            ready = self._should_process_segments()

        if not ready:
            logging.debug("Waiting for channels and playlist")
            async with self._cond:
                await self._cond.wait_for(self._should_process_segments)
        self._first = False
        wait_end = datetime.now(tz=UTC)
        logging.info("Channels/playlists changed after %s", wait_end - wait_start)

        processing_start = datetime.now(tz=UTC)
        processed = copy(await self.get_playlist())
        channels = await self.get_channels()
        logging.info("Starting to process segments...")
        for segment in processed.segments:
            seg_match = None
            # Clean-up the title
            for pattern in cleanup_title:
                segment.title = pattern.sub("", segment.title)
            segment.title = segment.title.strip()

            # Look for the closest match with the available channel names
            for channel in channels.findall("channel"):
                if difflib.get_close_matches(
                    segment.title,
                    [c.text for c in channel.findall("display-name")],
                    cutoff=cutoff,
                ):
                    logging.debug(
                        "%s -> %s", segment.title, channel.find("display-name").text
                    )
                    seg_match = channel.get("id")
                    break
            else:
                logging.debug(
                    "Could not match %r to any channel (cleaned: %r)",
                    segment.title,
                    segment.title,
                )
                continue

            # Save the match
            segment.custom_parser_values[StateAttrs.EXTINF]["tvg-id"] = seg_match

        processing_end = datetime.now(tz=UTC)
        logging.info("Segments processed after %s", processing_end - processing_start)
        async with self._lock:
            self._processed_playlist = processed
        self._processing_done.set()
