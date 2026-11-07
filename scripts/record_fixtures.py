"""Record scrubbed CJA API responses for use as test fixtures.

Run this yourself with your own credentials. It makes read-only GET requests:

    python scripts/record_fixtures.py --config myconfig.json --dataview dv_123

It saves the first two pages of data views, dimensions and metrics for one
data view, using a small page size so that there is a second page. It also
saves one data view, one dimension and one metric.

Before saving, every string value is replaced with a placeholder, except for
values under keys listed in KEEP_KEYS, e.g. "type". The same input string always
gets the same placeholder, so IDs still match across files. Numbers, booleans,
nulls and the response keys themselves are kept.

Check the output by hand before you commit any of it.
"""

import argparse
import json
from pathlib import Path

import cjapy


# Keys whose string values are API enums rather than customer data.
KEEP_KEYS = {
    "type", "dataType", "schemaType", "sourceFieldType", "dataSetType",
    "polarity", "precision", "includeType", "componentType", "timezoneDesignator",
    "containerNames", "bucketingSetting", "noValueOptionsSetting", "persistenceSetting",
    "defaultDimensionSort", "includeExcludeSetting", "fieldDefinition", "allocation",
    "expiration", "granularity", "func", "sortOrder", "segmentable", "status",
}

PAGE_KEYS = ("last", "lastPage", "first", "firstPage", "number", "numberOfElements",
             "size", "totalElements", "totalPages")


class Scrubber:
    def __init__(self):
        self.mapping = {}

    def placeholder(self, value):
        if value not in self.mapping:
            self.mapping[value] = "str_{}".format(len(self.mapping) + 1)
        return self.mapping[value]

    def scrub(self, value, key=None):
        if isinstance(value, dict):
            return {k: self.scrub(v, k) for k, v in value.items()}
        if isinstance(value, list):
            # Lists of enum values (e.g. containerNames) keep the parent key's rule.
            return [self.scrub(v, key) for v in value]
        if isinstance(value, str):
            if key in KEEP_KEYS:
                return value
            return self.placeholder(value)
        return value


def get_pages(connector, url, params, pages=2):
    """Return up to `pages` raw responses, starting at page 0."""
    results = []
    for page in range(pages):
        res = connector.getData(url, params=dict(params, page=page))
        results.append(res)
        if not isinstance(res, dict) or res.get("lastPage", res.get("last")) is not False:
            break
    return results


def page_keys(responses):
    return [{k: r.get(k) for k in PAGE_KEYS if k in r} for r in responses if isinstance(r, dict)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, type=Path, help="cjapy config JSON file")
    parser.add_argument("--dataview", required=True, help="data view ID to record")
    parser.add_argument("--out", type=Path, default=Path("tests/fixtures/recorded"))
    parser.add_argument("--page-size", type=int, default=2)
    args = parser.parse_args()

    cjapy.importConfigFile(str(args.config))
    cja = cjapy.CJA()
    base = cja.endpoint + "/data"
    dv = args.dataview
    size = args.page_size

    raw = {
        "dataviews_pages": get_pages(cja.connector, base + "/dataviews", {"limit": size}),
        "dimensions_pages": get_pages(cja.connector, base + f"/dataviews/{dv}/dimensions", {"limit": size}),
        "metrics_pages": get_pages(cja.connector, base + f"/dataviews/{dv}/metrics", {"limit": size}),
        "dataview": cja.getDataView(dv),
    }
    first_dimension = (raw["dimensions_pages"][0].get("content") or [{}])[0].get("id")
    first_metric = (raw["metrics_pages"][0].get("content") or [{}])[0].get("id")
    if first_dimension:
        raw["dimension"] = cja.getDimension(dv, first_dimension)
    if first_metric:
        raw["metric"] = cja.getMetric(dv, first_metric)

    print("Pagination keys seen (before scrubbing):")
    for name in ("dataviews_pages", "dimensions_pages", "metrics_pages"):
        print(" ", name, page_keys(raw[name]))

    scrubber = Scrubber()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, value in raw.items():
        path = args.out / f"{name}.json"
        path.write_text(json.dumps(scrubber.scrub(value), indent=2, sort_keys=True) + "\n")
        print("wrote", path)
    print(f"Replaced {len(scrubber.mapping)} distinct strings. Review the files before committing.")


if __name__ == "__main__":
    main()
