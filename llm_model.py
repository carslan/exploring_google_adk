from typing import Any, Dict, List, Union, Tuple

def build_catalog_and_payload(
    records: Union[List[Dict[str, Any]], Dict[str, Any]],
    prefix: str = "",
    catalog: Dict[str, str] = None
) -> Tuple[Dict[str, str], Union[List[Dict[str, Any]], Dict[str, Any]]]:
    """
    Builds catalog (descriptor) and encodes the payload recursively.
    Returns: (catalog, encoded_payload)

    catalog -> { "1": "profile.name", "2": "addresses.city", ... }
    payload -> with numeric keys based on catalog
    """
    if catalog is None:
        catalog = {}

    # helper: get or create ID for a path
    def _get_id(path: str) -> str:
        for k, v in catalog.items():
            if v == path:
                return k
        key = str(len(catalog) + 1)
        catalog[key] = path
        return key

    if isinstance(records, list):
        encoded_list = []
        for rec in records:
            if isinstance(rec, dict):
                encoded_list.append(build_catalog_and_payload(rec, prefix, catalog)[1])
            else:
                encoded_list.append(rec)
        return catalog, encoded_list

    elif isinstance(records, dict):
        encoded_dict = {}
        for key, value in records.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                _, nested_payload = build_catalog_and_payload(value, path, catalog)
                encoded_dict[_get_id(path)] = nested_payload
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    _, nested_payload = build_catalog_and_payload(value, path, catalog)
                    encoded_dict[_get_id(path)] = nested_payload
                else:
                    encoded_dict[_get_id(path)] = value
            else:
                encoded_dict[_get_id(path)] = value
        return catalog, encoded_dict

    return catalog, records


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

    catalog, payload = build_catalog_and_payload(data)
    print("Catalog:")
    print(catalog)
    print("\nEncoded Payload:")
    print(payload)
