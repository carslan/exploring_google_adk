from typing import Any, Dict, List, Union

def build_catalog(
    records: Union[List[Dict[str, Any]], Dict[str, Any]],
    prefix: str = "",
    catalog: Dict[str, str] = None
) -> Dict[str, str]:
    """
    Recursively scans given dict/list of dicts and creates a catalog
    mapping of flattened key paths to unique numeric IDs.

    Example output:
    {
        "1": "id",
        "2": "profile.name",
        "3": "profile.age",
        "4": "addresses.type",
        "5": "addresses.city"
    }
    """
    if catalog is None:
        catalog = {}

    if isinstance(records, list):
        for rec in records:
            if isinstance(rec, dict):
                build_catalog(rec, prefix, catalog)
        return catalog

    if isinstance(records, dict):
        for key, value in records.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                build_catalog(value, path, catalog)
            elif isinstance(value, list):
                # if list of dicts, dive into structure of first element
                if value and isinstance(value[0], dict):
                    build_catalog(value[0], path, catalog)
                else:
                    catalog[str(len(catalog) + 1)] = path
            else:
                catalog[str(len(catalog) + 1)] = path
        return catalog

    return catalog


# ---------------- Example ----------------
if __name__ == "__main__":
    data = [
        {
            "id": 1,
            "profile": {"name": "John", "age": 32},
            "addresses": [
                {"type": "home", "city": "NY"},
                {"type": "work", "city": "LA"}
            ]
        },
        {
            "id": 2,
            "profile": {"name": "Maria", "age": 28},
            "addresses": [{"type": "home", "city": "Rio"}]
        }
    ]

    catalog = build_catalog(data)
    print(catalog)
