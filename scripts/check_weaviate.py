"""Check whether the Weaviate BawnMystery collection is populated or empty."""
import os
import sys
import weaviate

_COLLECTION = "BawnMystery"
_WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8080")


def main():
    url_no_scheme = _WEAVIATE_URL.replace("https://", "").replace("http://", "")
    host, port = (url_no_scheme.rsplit(":", 1) + ["8080"])[:2]

    with weaviate.connect_to_local(host=host, port=int(port)) as client:
        if not client.collections.exists(_COLLECTION):
            print(f"Collection '{_COLLECTION}' does not exist.")
            sys.exit(1)

        collection = client.collections.get(_COLLECTION)
        count = collection.aggregate.over_all(total_count=True).total_count

    if count == 0:
        print(f"Collection '{_COLLECTION}' is EMPTY (0 objects).")
        sys.exit(1)

    print(f"Collection '{_COLLECTION}' is POPULATED ({count} objects).")


if __name__ == "__main__":
    main()
