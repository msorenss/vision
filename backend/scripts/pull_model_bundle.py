from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Download a model bundle zip from a"
            " Builder API and extract it locally."
            " Intended for Raspberry Pi Runners."
        )
    )
    parser.add_argument(
        "--builder",
        required=True,
        help="Base URL of Builder API, e.g. http://builder-host:8000",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output directory, e.g. /models/demo/v1",
    )
    parser.add_argument(
        "--endpoint",
        default="/api/v1/models/bundle",
        help="Bundle endpoint (default: /api/v1/models/bundle)",
    )
    args = parser.parse_args()

    url = args.builder.rstrip("/") + args.endpoint
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    req = Request(url, headers={"User-Agent": "vision-pull/0.1"})
    with urlopen(req, timeout=60) as resp:  # noqa: S310
        if resp.status != 200:
            raise SystemExit(f"Download failed: HTTP {resp.status}")
        data = resp.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        # Extract into a temp dir first, then copy into place.
        zf.extractall(out_dir)

    print(f"Extracted bundle to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
