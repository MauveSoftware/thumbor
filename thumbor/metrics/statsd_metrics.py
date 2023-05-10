#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

import statsd
from thumbor.metrics import BaseMetrics
from socket import gaierror
from thumbor.utils import logger

class Metrics(BaseMetrics):
    @classmethod
    def new_client(cls, config):
        try:
            return statsd.StatsClient(
                config.STATSD_HOST, config.STATSD_PORT, config.STATSD_PREFIX
            )
        except gaierror:
            logger.error("could not resolve statsd endpoint")
            return None

    @classmethod
    def client(cls, config):
        """
        Cache statsd client so it doesn't do a DNS lookup
        over and over
        """
        if not hasattr(cls, "_client") or cls._client == None:
            cls._client = Metrics.new_client(config)
        return cls._client

    def incr(self, metricname, value=1):
        cl = Metrics.client(self.config)
        if cl == None:
            return

        cl.incr(metricname, value)

    def timing(self, metricname, value):
        cl = Metrics.client(self.config)
        if cl == None:
            return

        cl.timing(metricname, value)

