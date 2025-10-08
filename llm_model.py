from typing import List, Dict, Any, Union

class CompactJSON:
    @staticmethod
    def encode(obj: Union[List, Dict]) -> Dict[str, Any]:
        """
        Recursively encodes dict or list into compact descriptor/payload structure.
        """
        if isinstance(obj, list):
            if not obj:
                return {"descriptor": {}, "payload": []}

            # collect all unique keys in all dicts
            all_keys = list({k for rec in obj if isinstance(rec, dict) for k in rec.keys()})
            descriptor = {str(i + 1): k for i, k in enumerate(all_keys)}
            key_map = {k: str(i + 1) for i, k in enumerate(all_keys)}

            payload = []
            for rec in obj:
                compact = {}
                for k, v in rec.items():
                    key = key_map[k]
                    if isinstance(v, (dict, list)):
                        compact[key] = CompactJSON.encode(v)
                    else:
                        compact[key] = v
                payload.append(compact)
            return {"descriptor": descriptor, "payload": payload}

        elif isinstance(obj, dict):
            if not obj:
                return {"descriptor": {}, "payload": {}}

            keys = list(obj.keys())
            descriptor = {str(i + 1): k for i, k in enumerate(keys)}
            key_map = {k: str(i + 1) for i, k in enumerate(keys)}

            payload = {}
            for k, v in obj.items():
                key = key_map[k]
                if isinstance(v, (dict, list)):
                    payload[key] = CompactJSON.encode(v)
                else:
                    payload[key] = v

            return {"descriptor": descriptor, "payload": payload}
        else:
            raise ValueError("Object must be dict or list of dicts")

    @staticmethod
    def decode(compact_obj: Dict[str, Any]) -> Union[List, Dict]:
        """
        Recursively decodes compacted JSON back to its original form.
        """
        descriptor = compact_obj.get("descriptor", {})
        payload = compact_obj.get("payload", {})

        if isinstance(payload, list):
            decoded_list = []
            for rec in payload:
                full = {}
                for k, v in rec.items():
                    name = descriptor.get(k)
                    if isinstance(v, dict) and "descriptor" in v and "payload" in v:
                        full[name] = CompactJSON.decode(v)
                    else:
                        full[name] = v
                decoded_list.append(full)
            return decoded_list

        elif isinstance(payload, dict):
            full = {}
            for k, v in payload.items():
                name = descriptor.get(k)
                if isinstance(v, dict) and "descriptor" in v and "payload" in v:
                    full[name] = CompactJSON.decode(v)
                else:
                    full[name] = v
            return full

        return payload


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
            "addresses": [
                {"type": "home", "city": "Rio"}
            ]
        }
    ]

    compact = CompactJSON.encode(data)
    print("Encoded:\n", compact)

    restored = CompactJSON.decode(compact)
    print("\nDecoded:\n", restored)
