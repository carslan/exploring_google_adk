from typing import Any, Dict, List, Union, Tuple

class AttributeDescriptor:
    def __init__(self, name: str, dtype: str = None, desc: str = None):
        self.name = name
        self.dtype = dtype
        self.desc = desc

    def to_dict(self):
        return {"name": self.name, "dtype": self.dtype, "desc": self.desc}

    def __repr__(self):
        return f"AttributeDescriptor(name={self.name!r}, dtype={self.dtype!r}, desc={self.desc!r})"


def build_catalog_and_payload(
    records: Union[List[Dict[str, Any]], Dict[str, Any]],
    descriptors: List[AttributeDescriptor],
    prefix: str = "",
    catalog: Dict[str, Dict[str, Any]] = None
) -> Tuple[Dict[str, Dict[str, Any]], Union[List[Dict[str, Any]], Dict[str, Any]]]:
    """
    Builds catalog and payload:
    - catalog maps numeric id -> descriptor info
    - payload replaces field names with numeric ids
    """
    if catalog is None:
        catalog = {}

    descriptor_map = {d.name: d for d in descriptors}

    def _get_id(path: str, field_name: str):
        for k, v in catalog.items():
            if v.get("path") == path:
                return k
        key = str(len(catalog) + 1)
        desc_obj = descriptor_map.get(field_name)
        catalog[key] = {
            "path": path,
            "descriptor": desc_obj.to_dict() if desc_obj else {"name": field_name}
        }
        return key

    if isinstance(records, list):
        encoded_list = []
        for rec in records:
            if isinstance(rec, dict):
                encoded_list.append(build_catalog_and_payload(rec, descriptors, prefix, catalog)[1])
            else:
                encoded_list.append(rec)
        return catalog, encoded_list

    elif isinstance(records, dict):
        encoded_dict = {}
        for key, value in records.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                _, nested_payload = build_catalog_and_payload(value, descriptors, path, catalog)
                encoded_dict[_get_id(path, key)] = nested_payload
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    _, nested_payload = build_catalog_and_payload(value, descriptors, path, catalog)
                    encoded_dict[_get_id(path, key)] = nested_payload
                else:
                    encoded_dict[_get_id(path, key)] = value
            else:
                encoded_dict[_get_id(path, key)] = value
        return catalog, encoded_dict

    return catalog, records


# ---------------- Example ----------------
if __name__ == "__main__":
    response = [
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

    descriptors = [
        AttributeDescriptor("id", dtype="int", desc="Unique identifier"),
        AttributeDescriptor("name", dtype="string", desc="Person name"),
        AttributeDescriptor("age", dtype="int", desc="Person age"),
        AttributeDescriptor("type", dtype="string", desc="Address type"),
        AttributeDescriptor("city", dtype="string", desc="City name"),
    ]

    catalog, payload = build_catalog_and_payload(response, descriptors)
    print("Catalog:\n", catalog)
    print("\nPayload:\n", payload)
