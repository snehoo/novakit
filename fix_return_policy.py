#!/usr/bin/env python3
"""
Adds the three missing MerchantReturnPolicy fields that Google Search Console
flagged across all Product pages (skill pages + bundle pages):
  - applicableCountry
  - returnMethod
  - returnFees

Parses and rewrites JSON-LD cleanly (no regex string-hacking).
Idempotent: skips files where applicableCountry is already present.
Run: python3 fix_return_policy.py [--dry-run] [files...]
"""
import re
import json
import sys
import glob

APPLICABLE_COUNTRY = "US"
RETURN_METHOD = "https://schema.org/ReturnByMail"
RETURN_FEES = "https://schema.org/FreeReturn"


def process_file(path, dry_run=False):
    content = open(path, encoding="utf-8").read()

    pattern = re.compile(
        r'(<script type="application/ld\+json">)\s*(\{.*?\})\s*(</script>)',
        re.DOTALL,
    )

    changed = False
    new_blocks = []

    for m in pattern.finditer(content):
        open_tag, raw, close_tag = m.group(1), m.group(2), m.group(3)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            new_blocks.append((m.start(), m.end(), m.group(0)))
            continue

        if data.get("@type") != "Product":
            new_blocks.append((m.start(), m.end(), m.group(0)))
            continue

        offer = data.get("offers", {})
        policy = offer.get("hasMerchantReturnPolicy", {})

        if "applicableCountry" in policy:
            return "skip (already patched)"

        policy["applicableCountry"] = APPLICABLE_COUNTRY
        policy["returnMethod"] = RETURN_METHOD
        policy["returnFees"] = RETURN_FEES
        offer["hasMerchantReturnPolicy"] = policy
        data["offers"] = offer

        new_json = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        new_block = f"{open_tag}{new_json}{close_tag}"
        new_blocks.append((m.start(), m.end(), new_block))
        changed = True

    if not changed:
        return "skip (no Product JSON-LD found or already patched)"

    result = content
    for start, end, replacement in reversed(new_blocks):
        result = result[:start] + replacement + result[end:]

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
    return "updated"


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    if args:
        files = args
    else:
        files = sorted(glob.glob("skills/*.html") + glob.glob("skills/bundles/*.html"))

    ok = skip = fail = 0
    for path in files:
        result = process_file(path, dry_run=dry_run)
        print(f"{path}: {result}")
        if result.startswith("updated"):
            ok += 1
        elif result.startswith("skip"):
            skip += 1
        else:
            fail += 1

    print(f"\nupdated: {ok}  skipped: {skip}  failed: {fail}")


if __name__ == "__main__":
    main()
