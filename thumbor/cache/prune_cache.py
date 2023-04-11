#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2023 Mauve Mailorder Software 

import os
from os.path import isdir
import sys

from thumbor.cache.expire_file import ExpireFile
from thumbor.cache.file_cache import FileCache

def prune_file_if_expired(f: str, file_cache: FileCache):
    expire_file = ExpireFile()
    if not expire_file.load(f):
        print(f'could not load expire file: {f}')
        return
    
    if expire_file.is_expired():
        print(f'delete {f}')
        file_cache.remove(f.replace(file_cache.EXPIRE_EXT, ""))


def prune_expired_links(dir: str, file_cache: FileCache):
    print(f'enter directory {dir}')
    for name in os.listdir(dir):
        f = os.path.join(dir, name)

        if os.path.isdir(f) and not name == "files":
            prune_expired_links(f, file_cache)
            return
            
        if os.path.isfile(f) and f.endswith(file_cache.EXPIRE_EXT):
            prune_file_if_expired(f, file_cache)
            return


def prune_expired_data_files_in_dir(dir: str):
    print(f'enter directory {dir}')
    for name in os.listdir(dir):
        f = os.path.join(dir, name)
        if os.path.isdir(f):
            prune_expired_data_files_in_dir(f)
            return

        stat = os.stat(f)
        if stat.st_nlink == 1:
            print(f'delete {f}')
            os.remove(f)


def prune_expired_data_files(dir: str):
    for name in os.listdir(dir):
        f = os.path.join(dir, name)
        if not os.path.isdir(f):
            continue

        files_dir = os.path.join(f, "files")
        if os.path.exists(files_dir):
            prune_expired_data_files_in_dir(files_dir)


dir = sys.argv[1]
if not os.path.exists(dir):
    print(f'path {dir} does not exist')
    os._exit(1)

file_cache = FileCache("", dir, 0)
print(f'Prune expired links')
prune_expired_links(dir, file_cache)

print(f'Prune data files not linked any more')
prune_expired_data_files(dir)
