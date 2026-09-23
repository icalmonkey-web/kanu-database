"""Read-only live discovery check; no API key, AI calls, or database writes."""
import argparse
import json
from playwright.sync_api import sync_playwright
from discovery import explore
from update_data import PORTAL_CONFIGS

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bank', default='中國信託')
    parser.add_argument('--pages', type=int, default=5)
    parser.add_argument('--channel', default=None)
    args = parser.parse_args()
    config = next(c for c in PORTAL_CONFIGS if c['bank'] == args.bank)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=args.channel)
        report = explore(browser.new_page(), config, lambda u, t: 'discovery_only', max_pages=args.pages)
        browser.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
