#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
#!/usr/bin/python
# -*- coding: utf-8 -*-

import re

from thumbor.loaders import http_loader

def _return_contents(response, url, context, req_start=None):
    result = http_loader.return_contents(response, url, context, req_start)

    if result.metadata is None:
        return result

    cache_control = result.metadata.get("Cache-Control")
    if cache_control is not None:
        _update_max_age(context, cache_control)
    else:
        context.request.max_age = 0

    return result

def _update_max_age(context, cache_control):
    match = re.search("s-maxage\\s*=\\s*(\\d+)", cache_control)
    if match:
        context.request.max_age_shared = int(match[1])

    match = re.search("max-age\\s*=\\s*(\\d+)", cache_control)
    if match:
        context.request.max_age = int(match[1])

    if context.request.max_age is not None or context.request.max_age_shared is not None:
        return

    context.request.max_age = 0

async def load(context, url):
    return await http_loader.load(context, url, return_contents_fn=_return_contents,)