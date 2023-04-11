#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

import hashlib
from json import dumps, loads
from os.path import dirname, splitext
from shutil import move
from uuid import uuid4

from thumbor.cache.file_cache import FileCache
import thumbor.storages as storages
from thumbor.utils import logger


class Storage(storages.BaseStorage):

    @property
    def cache(self):
        return FileCache("STORAGE", 
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
        return path


    async def get(self, path):
        if self.context.request.bypass_cache:
            logger.info("[STORAGE] bypassing cache for %s", self.context.request.url)
            return None

        abs_path = self.path_on_filesystem(path)
        res = self.cache.get(abs_path)
        if not res.found:
            return None

        return res.data


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

        found, _, _ = self.cache.exists(path_on_filesystem)
        return found


    async def remove(self, path):
        n_path = self.path_on_filesystem(path)
        self.cache.remove(n_path)


    async def put_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            return

        file_abspath = self.path_on_filesystem(path)
        file_dir_abspath = dirname(file_abspath)

        self.ensure_dir(file_dir_abspath)

        if not self.context.server.security_key:
            raise RuntimeError(
                "STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be "
                "True if no SECURITY_KEY specified"
            )

        crypto_path = "%s.txt" % splitext(file_abspath)[0]
        temp_abspath = "%s.%s" % (crypto_path, str(uuid4()).replace("-", ""))
        with open(temp_abspath, "wb") as _file:
            _file.write(self.context.server.security_key.encode())

        move(temp_abspath, crypto_path)
        logger.debug(
            "Stored crypto at %s (security key: %s)",
            crypto_path,
            self.context.server.security_key,
        )

        return file_abspath


    async def put_detector_data(self, path, data):
        file_abspath = self.path_on_filesystem(path)

        path = "%s.detectors.txt" % splitext(file_abspath)[0]
        temp_abspath = "%s.%s" % (path, str(uuid4()).replace("-", ""))

        file_dir_abspath = dirname(file_abspath)
        self.ensure_dir(file_dir_abspath)

        with open(temp_abspath, "w") as _file:
            _file.write(dumps(data))

        move(temp_abspath, path)

        return file_abspath


    async def get_detector_data(self, path):
        file_abspath = self.path_on_filesystem(path)
        path = "%s.detectors.txt" % splitext(file_abspath)[0]

        resource_available = await self.exists(path, path_on_filesystem=path)

        if not resource_available:
            return None

        return loads(open(path, "r").read())
