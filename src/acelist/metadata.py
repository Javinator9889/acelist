from __future__ import annotations

import importlib.metadata


version = importlib.metadata.version("acelist")
description = importlib.metadata.metadata("acelist").get("description")
license = importlib.metadata.metadata("acelist").get("license")
authors = importlib.metadata.metadata("acelist").get("author")
url = importlib.metadata.metadata("acelist").get("home-page")

__all__ = ["version", "description", "license", "authors", "url"]
