#!/usr/bin/env python3
"""Run the original strict assembler with its device grid cached per database.

The assembler reads this metadata without changing it. Reusing its Grid object
avoids rebuilding the entire XC7K480T grid for each unused I/O bank tile.
Feature parsing, lookup, required features and frame generation are unchanged.
"""
from functools import lru_cache

from utils import fasm2frames


class CachedGridDatabase(fasm2frames.Database):
    @lru_cache(maxsize=1)
    def grid(self):
        return super().grid()


def main():
    fasm2frames.Database = CachedGridDatabase
    fasm2frames.main()


if __name__ == '__main__':
    main()
