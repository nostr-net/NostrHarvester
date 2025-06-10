#!/usr/bin/env python3
"""
Run database migrations against the configured PostgreSQL instance.
"""
import asyncio

from common.storage import Storage


async def main():
    storage = Storage()
    await storage.initialize()


if __name__ == "__main__":
    asyncio.run(main())