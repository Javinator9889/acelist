from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
import argparse
import asyncio
import logging
import re
import sys

from .updater import updater
from .http import WebServer
from .editor import modify_m3u8_uri
from .matcher import Matcher, dumps

if TYPE_CHECKING:
    from asyncio import Task
    from typing import Awaitable


logging.basicConfig(level=logging.INFO)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--playlist-url", help="URL to the M3U8 playlist", required=True
    )
    parser.add_argument("--xmltv-url", help="URL to the XMLTV file", required=True)
    parser.add_argument(
        "--cleanup-re", help="Regex to cleanup the title", action="append"
    )
    parser.add_argument(
        "--listen-host", help="Listen address for the HTTP server", default="0.0.0.0"
    )
    parser.add_argument(
        "--listen-port", help="Listen port for the HTTP server", type=int, default=8080
    )
    parser.add_argument(
        "--interval", help="Update interval in seconds", type=int, default=600
    )
    parser.add_argument(
        "--cutoff", help="Cutoff for looking for name matches", type=float, default=0.95
    )
    parser.add_argument(
        "--output",
        help="Dump contents to a file instead of running the web server",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--scheme",
        help="New connection scheme. Only used when --output is set.",
        default="http",
    )
    parser.add_argument(
        "--host",
        help="New connection host. Only used when --output is set.",
        default="localhost",
    )
    parser.add_argument(
        "--port",
        help="New connection port. Only used when --output is set.",
        type=int,
        default=6878,
    )
    parser.add_argument(
        "--unique-id",
        help="Whether a unique ID should be generated. Only used when --output is set.",
        action="store_true",
    )
    parser.add_argument(
        "--log-level",
        help="Adjust the logging level",
        choices=logging.getLevelNamesMapping().keys(),
        default="INFO",
    )
    args = parser.parse_args(argv)
    if args.cleanup_re:
        args.cleanup_re = [re.compile(r) for r in args.cleanup_re]
    logging.getLogger().setLevel(args.log_level)
    return args


async def file_writer(
    args: argparse.Namespace, matcher: Matcher, tasks: Awaitable[tuple[Task]]
) -> int:
    t = await tasks
    out = await matcher.get_processed_playlist()
    out = modify_m3u8_uri(out, args.unique_id, args.scheme, args.host, args.port)
    with args.output.open("w") as f:
        f.write(dumps(out))

    for task in t:
        task.cancel()
    await asyncio.gather(*t, return_exceptions=True)
    return 0


def main() -> int:
    args = parse_args(sys.argv[1:])
    matcher = Matcher()
    tasks = updater(
        matcher,
        args.playlist_url,
        args.xmltv_url,
        args.cleanup_re,
        args.cutoff,
        args.interval,
        args.interval,
    )
    if args.output:
        return asyncio.run(file_writer(args, matcher, tasks))

    server = WebServer(args.listen_host, args.listen_port, matcher, tasks)
    return server()


if __name__ == "__main__":
    sys.exit(main())
