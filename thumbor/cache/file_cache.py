#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2023 Mauve Mailorder Software 

import hashlib
import os
from thumbor.cache.expire_file import ExpireFile

from thumbor.utils import logger

class FileCacheResult:
    def __init__(self, found: bool, data: bytes = bytes(), max_age = None, max_age_shared = None):
        self.found = found
        self.data = data
        self.max_age = max_age
        self.max_age_shared = max_age_shared


class FileCache:
    EXPIRE_EXT = ".max_age"

    def __init__(self, name: str, base_path: str, default_max_age: int):
        self.name = name
        self.base_path = base_path
        self.default_max_age = default_max_age


    def put(self, path: str, data, max_age: int, max_age_shared):
        data_file_path = self.data_file_path(data)
        symlink_dir = os.path.dirname(path)
        self.ensure_dir(symlink_dir)
        logger.debug(
            f"[{self.name}] putting at {path} (linked to: {data_file_path})"
        )
        self.ensure_data_file_exists(data_file_path, data)
        expire_file_path = path + self.EXPIRE_EXT
        self.write_expire_file(expire_file_path, max_age, max_age_shared)

        if os.path.exists(path):
            os.remove(path)

        os.symlink(data_file_path, path)


    def get(self, path):
        exists, max_age, max_age_shared = self.exists(path)
        if not exists:
            return FileCacheResult(False)
        
        with open(path, "rb") as source_file:
            return FileCacheResult(True, source_file.read(), max_age, max_age_shared)


    def exists(self, path):
        expire_file = ExpireFile(self.default_max_age)
        if not expire_file.load(path + self.EXPIRE_EXT):
            logger.debug(
                f"[{self.name}] no expire file found for {path}"
            )
            return False, None, None

        if expire_file.is_expired():
            return False, None, None
        
        return os.path.exists, expire_file.max_age, expire_file.max_age_shared


    def write_expire_file(self, path, max_age, max_age_shared):
        expire_file = ExpireFile(0)
        expire_file.set_max_age(max_age)
    
        if max_age_shared is not None:
            expire_file.set_max_age_shared(max_age_shared)

        expire_file.save(path)


    def ensure_data_file_exists(self, path, data):
        if os.path.exists(path):
            return

        dir = os.path.dirname(path)
        self.ensure_dir(dir)

        with open(path, "wb") as _file:
            _file.write(data)


    def data_file_path(self, hash_data):
        digest = hashlib.sha1(hash_data).hexdigest()

        return "%s/files/%s/%s/%s" % (
            self.base_path,
            digest[:2],
            digest[2:4],
            digest[4:],
        )


    def ensure_dir(self, path):
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as err:
                # FILE ALREADY EXISTS = 17
                if err.errno != 17:
                    raise


    def remove(self, path):
        if os.path.exists(path):
            os.remove(path)

        expire_file_path = path + self.EXPIRE_EXT
        if os.path.exists(expire_file_path):
            os.remove(expire_file_path)
