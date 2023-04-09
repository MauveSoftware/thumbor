#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

import hashlib
import os
from datetime import datetime
from json import dumps, loads
from os import symlink, remove
from os.path import dirname, exists, getmtime, splitext
from shutil import move

import thumbor.storages as storages
from thumbor.utils import logger


class Storage(storages.BaseStorage):
    EXPIRE_EXT = ".max_age"

    async def put(self, path, file_bytes):
        if self.context.request.max_age_shared is not None and self.context.request.max_age_shared == 0:
            return

        if self.context.request.max_age_shared is None and self.context.request.max_age is not None and self.context.request.max_age == 0:
            return

        symlink_abspath = self.path_on_filesystem(path)
        datafile_abspath = self.data_file_path(file_bytes)
        symlink_dir = dirname(symlink_abspath)
        self.ensure_dir(symlink_dir)
        logger.debug(
            "[STORAGE] putting at %s (linked to: %s)", symlink_abspath, datafile_abspath
        )
        self.ensure_data_file_exists(datafile_abspath, file_bytes)

        if self.context.request.max_age is not None:
            expirefile_abspath = symlink_abspath + Storage.EXPIRE_EXT
            with open(expirefile_abspath, "wb") as _file:
                self.write_expire_file(_file)

        if exists(symlink_abspath):
            remove(symlink_abspath)

        symlink(datafile_abspath, symlink_abspath)
        return path

    def write_expire_file(self, _file):
        _file.write(str.encode(str(self.context.request.max_age)))
        
        if self.context.request.max_age_shared is not None:
            _file.write(str.encode("," + str(self.context.request.max_age_shared)))

    def ensure_data_file_exists(self, path, data):
        if exists(path):
            return

        dir = dirname(path)
        self.ensure_dir(dir)

        with open(path, "wb") as _file:
            _file.write(data)

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

    async def get(self, path):
        if self.context.request.bypass_cache:
            logger.info("[STORAGE] bypassing cache for %s", self.context.request.url)
            return None

        abs_path = self.path_on_filesystem(path)

        resource_available = await self.exists(path, path_on_filesystem=abs_path)
        if not resource_available:
            return None

        max_age, max_age_shared = self.get_expire_time(abs_path)
        if max_age is not None:
            self.context.request.max_age = max_age
            self.context.request.max_age_shared = max_age_shared

        with open(self.path_on_filesystem(path), "rb") as source_file:
            return source_file.read()

    async def get_crypto(self, path):
        file_abspath = self.path_on_filesystem(path)
        crypto_file = "%s.txt" % (splitext(file_abspath)[0])

        if not exists(crypto_file):
            return None

        with open(crypto_file, "r") as crypto_f:
            return crypto_f.read()

    async def get_detector_data(self, path):
        file_abspath = self.path_on_filesystem(path)
        path = "%s.detectors.txt" % splitext(file_abspath)[0]

        resource_available = await self.exists(path, path_on_filesystem=path)

        if not resource_available:
            return None

        return loads(open(path, "r").read())

    def data_file_path(self, hash_data):
        digest = hashlib.sha1(hash_data).hexdigest()
        return "%s/files/%s/%s/%s" % (
            self.context.config.FILE_STORAGE_ROOT_PATH.rstrip("/"),
            digest[:2],
            digest[2:4],
            digest[4:],
        )

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

        max_age, max_age_shared = self.get_expire_time(path_on_filesystem)
        expire_time = max_age
        if max_age_shared is not None:
            expire_time = max_age_shared

        return exists(path_on_filesystem) and not self.__is_expired(path_on_filesystem, expire_time)

    async def remove(self, path):
        n_path = self.path_on_filesystem(path)

        expire_file = n_path + Storage.EXPIRE_EXT
        if exists(expire_file):
            os.remove(expire_file)

        return os.remove(n_path)

    def __is_expired(self, path, expire_in_seconds):
        if expire_in_seconds is None or expire_in_seconds == 0:
            return False

        timediff = datetime.now() - datetime.fromtimestamp(getmtime(path))
        return timediff.total_seconds() > expire_in_seconds

    def get_expire_time(self, path):
        file_abspath = path + Storage.EXPIRE_EXT

        if not exists(file_abspath):
            return self.context.config.get("STORAGE_EXPIRATION_SECONDS", None), None

        with open(file_abspath, "rb") as expire_file:
            buffer = expire_file.read()
            max_ages = buffer.decode().split(",")
            if len(max_ages) == 2:
                return int(max_ages[0]), int(max_ages[1])

            return int(max_ages[0]), None
