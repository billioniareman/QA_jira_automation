"""Quick Jira connectivity test using credentials from .env via config.settings.

Usage:
    python test_jira_connection.py
"""

from __future__ import annotations

import sys
from typing import Tuple

import requests

from config import settings


def _validate_config() -> Tuple[bool, str]:
    if not settings.JIRA_BASE_URL or "your-domain.atlassian.net" in settings.JIRA_BASE_URL:
        return False, "JIRA_BASE_URL is not set correctly in .env"
    if not settings.JIRA_USERNAME or settings.JIRA_USERNAME == "mock_user":
        return False, "JIRA_USERNAME is not set correctly in .env"
    if not settings.JIRA_API_TOKEN or settings.JIRA_API_TOKEN == "mock_token":
        return False, "JIRA_API_TOKEN is not set correctly in .env"
    return True, "ok"


def test_jira_connection() -> int:
    ok, message = _validate_config()
    if not ok:
        print(f"❌ Config error: {message}")
        return 1

    base_url = settings.JIRA_BASE_URL.rstrip("/")
    auth = (settings.JIRA_USERNAME, settings.JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}

    print(f"🔎 Testing Jira connection: {base_url}")

    try:
        # 1) Validate authentication by calling /myself (v3 first, then v2 fallback)
        me_resp = requests.get(
            f"{base_url}/rest/api/3/myself", auth=auth, headers=headers, timeout=20
        )
        if me_resp.status_code == 404:
            me_resp = requests.get(
                f"{base_url}/rest/api/2/myself", auth=auth, headers=headers, timeout=20
            )

        if me_resp.status_code != 200:
            print("❌ Authentication failed")
            print(f"   Status: {me_resp.status_code}")
            print(f"   Response: {me_resp.text[:500]}")
            auth_header = me_resp.headers.get("www-authenticate")
            if auth_header:
                print(f"   WWW-Authenticate: {auth_header}")

            if me_resp.status_code == 401:
                print("\nLikely causes:")
                print("1) JIRA_USERNAME must be your Atlassian account email")
                print("2) JIRA_API_TOKEN is invalid/revoked/expired")
                print("3) API token was generated from a different Atlassian account")
                print("4) The account has no access to this Jira site")
                print("5) .env values include hidden spaces or quotes")

            return 1

        me_data = me_resp.json()
        print("✅ Authentication successful")
        print(
            "   User: "
            f"{me_data.get('displayName', 'N/A')} "
            f"<{me_data.get('emailAddress', 'hidden or unavailable')}>"
        )

        # 2) Validate issue read access with a small JQL search
        search_url = f"{base_url}/rest/api/2/search"
        params = {
            "jql": "project IS NOT EMPTY ORDER BY created DESC",
            "maxResults": 1,
            "fields": "key,summary",
        }
        search_resp = requests.get(
            search_url,
            auth=auth,
            headers=headers,
            params=params,
            timeout=20,
        )

        if search_resp.status_code != 200:
            print("❌ Jira API reachable, but issue search failed")
            print(f"   Status: {search_resp.status_code}")
            print(f"   Response: {search_resp.text[:500]}")
            return 1

        total = search_resp.json().get("total", 0)
        print(f"✅ Jira search successful (visible issues: {total})")
        print("🎉 Jira connection test passed")
        return 0

    except requests.RequestException as exc:
        print(f"❌ Network/request error: {exc}")
        return 1
    except ValueError as exc:
        print(f"❌ Invalid JSON response from Jira: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(test_jira_connection())
