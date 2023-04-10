#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) Mauve Mailorder Software

import os.path
from datetime import datetime

class ExpireFile:
    def __init__(self, default_expiration: int):
        self.max_age = default_expiration
        self.max_age_shared = None
        self.change_date = datetime.now()


    def set_max_age(self, val: int):
        self.max_age = val


    def set_max_age_shared(self, val: int):
        self.max_age_shared = val


    def load(self, path: str):
        if not os.path.exists(path):
            return False

        self.change_date = datetime.fromtimestamp(os.path.getmtime(path))

        with open(path) as expire_file:
            content = expire_file.read()

        max_ages = content.split(",")
        self.max_age = int(max_ages[0])

        if len(max_ages) > 1:
            self.max_age_shared = int(max_ages[1])

        return True


    def save(self, path: str): 
        with open(path, "wb") as _file:
            self.__write(_file)


    def __write(self, _file):
        max_age = self.max_age
        if max_age is None:
            max_age = 0

        _file.write(str.encode(str(max_age)))
        
        if self.max_age_shared is not None:
            _file.write(str.encode("," + str(self.max_age_shared)))


    def is_expired(self):
        timediff = datetime.now() - self.change_date;

        if self.max_age_shared is not None:
            return timediff.total_seconds() > self.max_age_shared

        return self.max_age is None or timediff.total_seconds() > self.max_age
