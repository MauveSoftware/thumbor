#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

import hashlib
from datetime import datetime
from os import symlink, remove
from os.path import abspath, dirname, exists, getmtime, isdir, isfile, join
from urllib.parse import unquote

import pytz

from thumbor.engines import BaseEngine
from thumbor.result_storages import BaseStorage, ResultStorageResult
from thumbor.utils import deprecated, logger

class Storage(BaseStorage):
    PATH_FORMAT_VERSION = "v2"
    EXPIRE_EXT = ".max_age"

    @property
    def is_auto_webp(self):
        return self.context.config.AUTO_WEBP and self.context.request.accepts_webp

    async def put(self, image_bytes):
        if self.context.request.max_age_shared is not None and self.context.request.max_age_shared == 0:
            return

        if self.context.request.max_age_shared is None and self.context.request.max_age is not None and self.context.request.max_age == 0:
            return

        symlink_abspath = self.normalize_path(self.context.request.url)
        if not self.validate_path(symlink_abspath):
            logger.warning(
                "[RESULT_STORAGE] unable to write outside root path: %s", symlink_abspath
            )
            return

        datafile_abspath = self.data_file_path(image_bytes)
        if not self.validate_path(datafile_abspath):
            logger.warning(
                "[RESULT_STORAGE] unable to write outside root path: %s", datafile_abspath
            )
            return

        symlink_dir = dirname(symlink_abspath)
        self.ensure_dir(symlink_dir)
        logger.debug(
            "[RESULT_STORAGE] putting at %s (linked to: %s)", symlink_abspath, datafile_abspath
        )
        self.ensure_data_file_exists(datafile_abspath, image_bytes)

        if self.context.request.max_age is not None:
            expirefile_abspath = symlink_abspath + Storage.EXPIRE_EXT
            with open(expirefile_abspath, "wb") as _file:
                self.write_expire_file(_file)

        if exists(symlink_abspath):
            remove(symlink_abspath)

        symlink(datafile_abspath, symlink_abspath)

    def ensure_data_file_exists(self, path, data):
        if exists(path):
            return

        dir = dirname(path)
        self.ensure_dir(dir)

        with open(path, "wb") as _file:
            _file.write(data)

    def write_expire_file(self, _file):
        _file.write(str.encode(str(self.context.request.max_age)))
        
        if self.context.request.max_age_shared is not None:
            _file.write(str.encode("," + str(self.context.request.max_age_shared)))

    async def get(self):
        if self.context.request.bypass_cache:
            logger.info("[RESULT_STORAGE] bypassing cache for %s", self.context.request.url)
            return None

        path = self.context.request.url
        file_abspath = self.normalize_path(path)

        if not self.validate_path(file_abspath):
            logger.warning(
                "[RESULT_STORAGE] unable to read from outside root path: %s",
                file_abspath,
            )
            return None

        logger.debug("[RESULT_STORAGE] getting from %s", file_abspath)

        if isdir(file_abspath):
            logger.warning(
                "[RESULT_STORAGE] cache location is a directory: %s", file_abspath
            )
            return None

        if not exists(file_abspath):
            logger.debug("[RESULT_STORAGE] image not found at %s", file_abspath)
            return None

        max_age, max_age_shared = self.get_expire_time(file_abspath)
        expire_time = max_age
        if max_age_shared is not None:
            expire_time = max_age_shared

        if self.is_expired(file_abspath, expire_time):
            logger.debug("[RESULT_STORAGE] cached image has expired")
            return None

        with open(file_abspath, "rb") as image_file:
            buffer = image_file.read()

        if max_age is not None:
            self.context.request.max_age = max_age
            self.context.request.max_age_shared = max_age_shared

        result = ResultStorageResult(
            buffer=buffer,
            metadata={
                "LastModified": datetime.fromtimestamp(getmtime(file_abspath)).replace(
                    tzinfo=pytz.utc
                ),
                "ContentLength": len(buffer),
                "ContentType": BaseEngine.get_mimetype(buffer),
            },
        )

        return result

    def validate_path(self, path):
        return abspath(path).startswith(
            self.context.config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH
        )

    def normalize_path(self, path):
        digest = hashlib.sha1(unquote(path).encode("utf-8")).hexdigest()

        return "%s/%s/%s/%s/%s" % (
            self.context.config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH.rstrip("/"),
            "auto_webp" if self.is_auto_webp else "default",
            digest[:2],
            digest[2:4],
            digest[4:],
        )

    def data_file_path(self, hash_data):
        digest = hashlib.sha1(hash_data).hexdigest()

        return "%s/files/%s/%s/%s" % (
            self.context.config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH.rstrip("/"),
            digest[:2],
            digest[2:4],
            digest[4:],
        )

    def partition(self, path_raw):
        path = path_raw.lstrip("/")
        return join("".join(path[0:2]), "".join(path[2:4]))

    def is_expired(self, path, expire_in_seconds):
        if expire_in_seconds is None or expire_in_seconds == 0:
            return False

        timediff = datetime.now() - datetime.fromtimestamp(getmtime(path))
        return timediff.total_seconds() > expire_in_seconds

    def get_expire_time(self, path):
        file_abspath = path + Storage.EXPIRE_EXT

        if not exists(file_abspath):
            return self.context.config.get("RESULT_STORAGE_EXPIRATION_SECONDS", None), None

        with open(file_abspath, "rb") as expire_file:
            buffer = expire_file.read()
            max_ages = buffer.decode().split(",")
            if len(max_ages) == 2:
                return int(max_ages[0]), int(max_ages[1])

            return int(max_ages[0]), None

    @deprecated("Use result's last_modified instead")
    def last_updated(self):
        path = self.context.request.url
        file_abspath = self.normalize_path(path)
        if not self.validate_path(file_abspath):
            logger.warning(
                "[RESULT_STORAGE] unable to read from outside root path: %s",
                file_abspath,
            )
            return True
        logger.debug("[RESULT_STORAGE] getting from %s", file_abspath)

        if not exists(file_abspath):
            logger.debug("[RESULT_STORAGE] image not found at %s", file_abspath)
            return True

        expire_time = self.get_expire_time(file_abspath)
        if self.is_expired(file_abspath, expire_time):
            logger.debug("[RESULT_STORAGE] image not found at %s", file_abspath)
            return True

        return datetime.fromtimestamp(getmtime(file_abspath)).replace(tzinfo=pytz.utc)
