#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

from functools import cache
import hashlib
from thumbor.cache.file_cache import FileCache

import thumbor.storages as storages
from thumbor.utils import logger


class Storage(storages.BaseStorage):
    def __init__(self, context):
        super().__init__(context)
        self.cache = FileCache("STORAGE", 
                               self.context.config.FILE_STORAGE_ROOT_PATH.rstrip("/"),
                               self.context.config.get("STORAGE_EXPIRATION_SECONDS", None))

    async def put(self, path, file_bytes):
        if self.context.request.max_age_shared is not None and self.context.request.max_age_shared == 0:
            return

        if self.context.request.max_age_shared is None and self.context.request.max_age is not None and self.context.request.max_age == 0:
            return

        file_abspath = self.path_on_filesystem(path)
        self.cache.put(file_abspath, 
                       file_bytes, 
                       self.context.request.max_age, 
                       self.context.request.max_age_shared)

    async def get(self, path):
        if self.context.request.bypass_cache:
            logger.info("[STORAGE] bypassing cache for %s", self.context.request.url)
            return None

        abs_path = self.path_on_filesystem(path)
        cache_res = self.cache.get(abs_path)
        if not cache_res.found:
            return None

        return cache_res.data

    def path_on_filesystem(self, hash_data):
        digest = hashlib.sha1(hash_data.encode("utf-8")).hexdigest()
        return "%s/%s/%s" % (
            self.context.config.FILE_STORAGE_ROOT_PATH.rstrip("/"),
            digest[:2],
            digest[2:],
        )

    async def exists(self, path, path_on_filesystem=None):  # pylint: disable=arguments-differ
        if path_on_filesystem is None:
            path_on_filesystem = self.path_on_filesystem(path)

        return self.cache.exists(path_on_filesystem)

    async def remove(self, path):
        n_path = self.path_on_filesystem(path)
        self.cache.remove(n_path)
