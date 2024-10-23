import re

from starlette.types import ASGIApp, Receive, Scope, Send

repeated_quotes = re.compile(r"//+")


class HttpUrlModifyMiddleware:
    """
    This http middleware modifies urls with repeated slashes to the cleaned up
    versions of the urls without redirecting
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and repeated_quotes.search(scope["path"]):
            scope["path"] = repeated_quotes.sub("/", scope["path"])
        await self.app(scope, receive, send)
