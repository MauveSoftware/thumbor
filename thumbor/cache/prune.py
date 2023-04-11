#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2023 Mauve Mailorder Software 

import os
import sys

from thumbor.cache.expire_file import ExpireFile
from thumbor.cache.file_cache import FileCache

def prune_file_if_expired(f: str, file_cache: FileCache):
    print(f'check if {f} is exired')
    expire_file = ExpireFile()
    if not expire_file.load(f):
        print(f'could not load expire file: {f}')
        return
    
    if expire_file.is_expired():
        print(f'delete {f}')
        file_cache.remove(f.replace(file_cache.EXPIRE_EXT, ""))


def prune_directory(dir: str, file_cache: FileCache):
    print(f'enter directory {dir}')
    for name in os.listdir(dir):
        f = os.path.join(dir, name)

        if os.path.isdir(f):
            prune_directory(f, file_cache)
            
        if os.path.isfile(f) and f.endswith(file_cache.EXPIRE_EXT):
            prune_file_if_expired(f, file_cache)


dir = sys.argv[1]
if not os.path.exists(dir):
    print(f'path {dir} does not exist')
    os._exit(1)

file_cache = FileCache("", dir, 0)
prune_directory(dir, file_cache)
