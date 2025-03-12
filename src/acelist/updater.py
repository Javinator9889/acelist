from __future__ import annotations

from typing import TYPE_CHECKING
from .matcher import Matcher

import aiohttp
import asyncio
import logging

if TYPE_CHECKING:
    from asyncio import Task
    import re


async def _playlist_updater(uri: str, interval: int, matcher: Matcher):
    self = asyncio.current_task()
    session = aiohttp.ClientSession()
    while not self.cancelled():
        try:
            async with session.get(uri) as response:
                logging.debug("Updating playlist, res: %s", response)
                res = await response.text()
                await matcher.set_playlist(res)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error("Error updating playlist: %s", e, exc_info=e)
    logging.info("Playlist updater finished")
    await session.close()


async def _channels_updater(uri: str, interval: int, matcher: Matcher):
    self = asyncio.current_task()
    session = aiohttp.ClientSession()
    while not self.cancelled():
        try:
            async with session.get(uri) as response:
                logging.debug("Updating channels, res: %s", response)
                res = await response.content.read()
                try:
                    await matcher.set_channels(res)
                except Exception as e:
                    logging.error("Error setting channels: %s", e, exc_info=e)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error("Error updating channels: %s", e, exc_info=e)
    logging.info("Channels updater finished")
    await session.close()


async def _segments_updater(
    cleanup_re: list[re.Pattern], cutoff: float, matcher: Matcher
):
    self = asyncio.current_task()
    while not self.cancelled():
        try:
            logging.debug("Updating segments")
            await matcher.update_segments(cleanup_re, cutoff)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error("Error updating segments: %s", e, exc_info=e)
    logging.info("Segments updater finished")


async def updater(
    matcher: Matcher,
    playlist_uri: str,
    channel_uri: str,
    segment_cleanup: list[re.Pattern],
    segment_cutoff: float,
    playlist_interval: int,
    channel_interval: int,
) -> tuple[Task]:
    playlist_task = asyncio.create_task(
        _playlist_updater(playlist_uri, playlist_interval, matcher)
    )
    channels_task = asyncio.create_task(
        _channels_updater(channel_uri, channel_interval, matcher)
    )
    segments_task = asyncio.create_task(
        _segments_updater(segment_cleanup, segment_cutoff, matcher)
    )
    await matcher.ready

    return playlist_task, channels_task, segments_task
