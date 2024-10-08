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

    cacheTTL = context.request_handler.request.headers.pop("X-Thumbor-Cache-TTL", None)
    if cacheTTL is not None:
        context.request.max_age_shared = int(cacheTTL)
        
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

def _normalize_url(url, context):
    url = http_loader.quote_url(url)

    if url.startswith("http:"):
        url = url.replace("http:", "https:", 1)

    if not url.startswith("https://"):
        url = "https://%s" % url

    backend_address = context.request_handler.request.headers.pop("X-Thumbor-Backend-Address", None)
    if backend_address is None:
        return url

    idx = url.index('/', 8)
    if idx < 0:
        return url

    return "https://" + backend_address + url[idx:]

async def load(context, url):
    normalize_url_func = lambda u: _normalize_url(u, context)
    return await http_loader.load(context, url, return_contents_fn=_return_contents,normalize_url_func=normalize_url_func)