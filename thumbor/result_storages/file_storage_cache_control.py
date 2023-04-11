#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

import hashlib
from datetime import datetime
from os.path import getmtime
from urllib.parse import unquote

import pytz

from thumbor.engines import BaseEngine
from thumbor.result_storages import BaseStorage, ResultStorageResult
from thumbor.utils import deprecated, logger
from thumbor.cache.file_cache import FileCache 

class Storage(BaseStorage):
    PATH_FORMAT_VERSION = "v2"

    @property
    def cache(self):
        return FileCache("RESULT_STORAGE", 
                         self.context.config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH.rstrip("/"),
                         0)

    @property
    def is_auto_webp(self):
        return self.context.config.AUTO_WEBP and self.context.request.accepts_webp


    async def put(self, image_bytes):
        if self.context.request.max_age_shared is not None and self.context.request.max_age_shared == 0:
            return

        if self.context.request.max_age_shared is None and self.context.request.max_age is not None and self.context.request.max_age == 0:
            return

        symlink_abspath = self.normalize_path(self.context.request.url)
        self.cache.put(symlink_abspath, 
                       image_bytes, 
                       self.context.request.max_age,
                       self.context.request.max_age_shared)


    async def get(self):
        if self.context.request.bypass_cache:
            logger.info("[RESULT_STORAGE] bypassing cache for %s", self.context.request.url)
            return None

        path = self.context.request.url
        file_abspath = self.normalize_path(path)
        res = self.cache.get(file_abspath)
        if not res.found:
            return None

        if res.max_age is not None:
            self.context.request.max_age = res.max_age
            self.context.request.max_age_shared = res.max_age_shared

        return ResultStorageResult(
            buffer=res.data,
            metadata={
                "LastModified": datetime.fromtimestamp(getmtime(file_abspath)).replace(
                    tzinfo=pytz.utc
                ),
                "ContentLength": len(res.data),
                "ContentType": BaseEngine.get_mimetype(res.data),
            },
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


    @deprecated("Use result's last_modified instead")
    def last_updated(self):
        path = self.context.request.url
        file_abspath = self.normalize_path(path)

        if not self.cache.exists(file_abspath):
            logger.debug("[RESULT_STORAGE] image not found or expired at %s", file_abspath)
            return True

        return datetime.fromtimestamp(getmtime(file_abspath)).replace(tzinfo=pytz.utc)
