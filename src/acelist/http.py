from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import Response, RedirectResponse
from typing import TYPE_CHECKING
import asyncio
import copy
import uvicorn

from .editor import modify_m3u8_uri
from .matcher import dumps
from .metadata import version, description, license, authors, url

if TYPE_CHECKING:
    from asyncio import Task
    from typing import Awaitable
    from .matcher import Matcher


class WebServer:
    def __init__(
        self,
        host: str,
        port: int,
        matcher: Matcher,
        tasks: Awaitable[tuple[Task]],
    ):
        self.host = host
        self.port = port
        self.matcher = matcher
        self.tasks = tasks
        self._app = FastAPI(
            title="AceList",
            version=version,
            description=description,
            license_info=license,
            contact=authors,
            lifespan=self.lifespan,
        )
        self._app.add_api_route("/", self._root_handler)
        self._app.add_api_route("/playlist", self._playlist_handler)

    async def _root_handler(self):
        """Redirects to the documentation."""
        return RedirectResponse(url="/docs")

    async def _playlist_handler(
        self,
        scheme: str = "http",
        host: str = "localhost",
        port: int = 6878,
        unique_id: bool = True,
    ):
        """Gets the latest playlist data, already matched with the XMLTV channels.
        Modifies each segment URI to point to the correct AceStream server, with
        a uniquely generated ID if requested.

        Args:
            scheme (:obj:`str`, optional): New connection scheme. Defaults to "http".
            host (:obj:`str`, optional): New connection host. Defaults to "localhost".
            port (:obj:`int`, optional): New connection port. Defaults to 6878.
            unique_id (:obj:`bool`, optional): Whether a unique ID should be generated.
                Defaults to True.

        Returns:
            :obj:`Response`: M3U8 playlist with modified URIs.
        """
        playlist = copy.deepcopy(await self.matcher.get_playlist())
        modified = modify_m3u8_uri(playlist, unique_id, scheme, host, port)
        return Response(
            content=dumps(modified), media_type="application/vnd.apple.mpegurl"
        )

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        tasks = await self.tasks
        yield
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def __call__(self, *args, **kwds) -> int:
        uvicorn.run(self._app, host=self.host, port=self.port, *args, **kwds)
        return 0
