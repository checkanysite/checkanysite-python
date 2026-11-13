"""Checks whether a site shows traces of an AI website builder.

The script uses our stored result for the site when there is one, and scans the
site when there isn't. Run it with your API key in the environment:

    export CHECKANYSITE_API_KEY="cas_live_…"
    python examples/quickstart.py stripe.com
"""

from __future__ import annotations

import sys

from checkanysite import CheckAnySite, NotFoundError
from checkanysite.models import SiteResult


def check(client: CheckAnySite, domain: str) -> SiteResult:
    """Returns the site's result, stored or from a new scan."""
    try:
        return client.sites.retrieve(domain, checks=["ai"])
    except NotFoundError:
        print(f"Scanning {domain}…")
        scan = client.scans.create_and_wait(domain, checks=["ai"])
        if scan.result is None:
            reason = scan.failure.message if scan.failure else scan.status
            sys.exit(f"The scan of {domain} failed: {reason}")
        return scan.result


def main(domain: str) -> None:
    with CheckAnySite() as client:
        site = check(client, domain)

    traces = site.ai
    if traces is None:
        sys.exit(f"The answer for {domain} has no AI builder check.")
    if traces.level == "none":
        print(f"No AI builder traces found on {site.domain}.")
    else:
        builders = ", ".join(builder.name for builder in traces.builders)
        print(f"{site.domain}: traces of {builders}, {traces.level} confidence")
    print(f"Evidence: {site.result_url}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "stripe.com")
