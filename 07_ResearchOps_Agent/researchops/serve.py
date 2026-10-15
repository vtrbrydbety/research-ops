"""Validated production launcher; bind and worker count are not CLI-overridable."""

import uvicorn

from researchops.core.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "apps.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=1,
        proxy_headers=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
