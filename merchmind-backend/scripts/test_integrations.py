#!/usr/bin/env python3
"""
Real integration health check script.
Hits every external service with live credentials and prints colored results.
Run from the merchmind-backend directory:
    python scripts/test_integrations.py
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── ANSI color codes ─────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

OK = f"{GREEN}✓ OK{RESET}"
FAIL = f"{RED}✗ FAIL{RESET}"
WARN = f"{YELLOW}⚠ DEGRADED{RESET}"
SKIP = f"{DIM}– SKIP{RESET}"


def fmt_result(result: dict) -> str:
    if result.get("ok"):
        ms = f" {DIM}({result.get('ms', '?')}ms){RESET}" if "ms" in result else ""
        return f"{OK}{ms}"
    if result.get("degraded"):
        return f"{WARN}  {DIM}{result.get('error', '')}{RESET}"
    return f"{FAIL}  {RED}{result.get('error', 'unknown error')}{RESET}"


def run_check(name: str, fn) -> tuple[str, dict]:
    try:
        result = fn()
        return name, result
    except Exception as e:
        return name, {"service": name, "ok": False, "error": str(e)}


def check_anthropic() -> dict:
    from app.utils.claude_client import claude
    try:
        text, usage = claude.haiku(
            "health_check",
            [{"role": "user", "content": "Reply with exactly: ok"}],
            max_tokens=4,
        )
        return {"service": "anthropic", "ok": text.strip().lower() == "ok"}
    except Exception as e:
        return {"service": "anthropic", "ok": False, "error": str(e)}


def check_printify() -> dict:
    from app.services.publishing.printify_publisher import get_printify_service
    return get_printify_service().health_check()


def check_shopify() -> dict:
    from app.services.publishing.shopify_publisher import get_shopify_service
    return get_shopify_service().health_check()


def check_instagram() -> dict:
    from app.services.marketing.instagram_service import get_instagram_service
    return get_instagram_service().health_check()


def check_tiktok() -> dict:
    from app.services.marketing.tiktok_service import get_tiktok_service
    return get_tiktok_service().health_check()


def check_pinterest() -> dict:
    from app.services.marketing.pinterest_service import get_pinterest_service
    return get_pinterest_service().health_check()


def check_klaviyo() -> dict:
    from app.services.marketing.klaviyo_service import get_klaviyo_service
    return get_klaviyo_service().health_check()


def check_google_trends() -> dict:
    from app.services.intelligence.google_trends import get_google_trends_service
    return get_google_trends_service().health_check()


def check_reddit() -> dict:
    from app.services.intelligence.reddit_scraper import get_reddit_scraper_service
    return get_reddit_scraper_service().health_check()


def check_twitter() -> dict:
    from app.services.intelligence.twitter_scraper import get_twitter_scraper_service
    return get_twitter_scraper_service().health_check()


def check_image_generator() -> dict:
    from app.services.design.image_generator import get_image_generator_service
    return get_image_generator_service().health_check()


def check_placeit() -> dict:
    from app.services.design.placeit_service import get_placeit_service
    return get_placeit_service().health_check()


CHECKS = {
    "Anthropic (Claude)": check_anthropic,
    "Printify": check_printify,
    "Shopify": check_shopify,
    "Instagram": check_instagram,
    "TikTok": check_tiktok,
    "Pinterest": check_pinterest,
    "Klaviyo": check_klaviyo,
    "Google Trends": check_google_trends,
    "Reddit": check_reddit,
    "Twitter/X": check_twitter,
    "Image Generator": check_image_generator,
    "Placeit": check_placeit,
}

CRITICAL = {"Anthropic (Claude)", "Printify", "Shopify"}


def main():
    print(f"\n{BOLD}{CYAN}MerchMind Integration Health Check{RESET}")
    print(f"{DIM}Running {len(CHECKS)} checks in parallel...{RESET}\n")

    start = time.monotonic()
    results: dict[str, dict] = {}

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(run_check, name, fn): name for name, fn in CHECKS.items()}
        for future in as_completed(futures):
            name, result = future.result()
            results[name] = result

    elapsed = round(time.monotonic() - start, 1)

    # Print results grouped: critical first, then others
    col_width = max(len(n) for n in results) + 2
    print(f"{'Service':<{col_width}} {'Status'}")
    print("─" * (col_width + 30))

    ok_count = 0
    fail_count = 0
    critical_fail = []

    for name in CHECKS:
        result = results[name]
        status = fmt_result(result)
        prefix = f"{BOLD}" if name in CRITICAL else ""
        suffix = f"{RESET}" if name in CRITICAL else ""
        print(f"{prefix}{name:<{col_width}}{suffix} {status}")
        if result.get("ok"):
            ok_count += 1
        else:
            fail_count += 1
            if name in CRITICAL:
                critical_fail.append(name)

    print("─" * (col_width + 30))
    print(f"\n{DIM}Completed in {elapsed}s{RESET}")
    print(f"{GREEN}{ok_count} passing{RESET}  {RED}{fail_count} failing{RESET}")

    if critical_fail:
        print(f"\n{RED}{BOLD}CRITICAL failures: {', '.join(critical_fail)}{RESET}")
        print(f"{RED}Pipeline will not function until these are resolved.{RESET}")
        sys.exit(1)
    elif fail_count > 0:
        print(f"\n{YELLOW}Non-critical failures detected. Pipeline will run with degraded features.{RESET}")
        sys.exit(0)
    else:
        print(f"\n{GREEN}{BOLD}All services healthy. Ready to run.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
