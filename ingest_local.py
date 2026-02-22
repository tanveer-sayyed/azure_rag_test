"""Index local .txt files from a directory into Weaviate using contextual retrieval."""
import os
import sys
import pathlib
import weaviate
import weaviate.classes.config as wvc_config
from weaviate.util import generate_uuid5

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src/webapp"))
from embeddings import split_chunks, contextualize_chunk, embed

_COLLECTION = "BawnMystery"


def _weaviate_client():
    """Connect to Weaviate using WEAVIATE_URL env var."""
    url = os.environ.get("WEAVIATE_URL", "http://localhost:8080").replace("https://", "").replace("http://", "")
    host, port = (url.rsplit(":", 1) + ["8080"])[:2]
    return weaviate.connect_to_local(host=host, port=int(port))


def _ensure_collection(client):
    """Create BawnMystery collection if absent."""
    if not client.collections.exists(_COLLECTION):
        client.collections.create(
            name=_COLLECTION,
            vectorizer_config=wvc_config.Configure.Vectorizer.none(),
            properties=[
                wvc_config.Property(name="content", data_type=wvc_config.DataType.TEXT),
                wvc_config.Property(name="source", data_type=wvc_config.DataType.TEXT),
            ],
        )


def index_directory(docs_dir: str):
    """Contextually enrich, embed, and upload all .txt files in docs_dir to Weaviate."""
    docs_path = pathlib.Path(docs_dir)
    client = _weaviate_client()
    _ensure_collection(client)
    collection = client.collections.get(_COLLECTION)

    for txt_file in sorted(docs_path.glob("*.txt")):
        document = txt_file.read_text()
        raw_chunks = split_chunks(document)
        print(f"contextualizing {txt_file.name} ({len(raw_chunks)} chunks)...")
        contextualized = [contextualize_chunk(document, c) for c in raw_chunks]
        vectors = embed(contextualized)

        with collection.batch.dynamic() as batch:
            for i, (chunk, vector) in enumerate(zip(contextualized, vectors)):
                batch.add_object(
                    properties={"content": chunk, "source": txt_file.name},
                    vector=vector,
                    uuid=generate_uuid5(f"{txt_file.name}-{i}"),
                )
        print(f"indexed {txt_file.name} ({len(raw_chunks)} chunks)")

    client.close()
    print("done.")


if __name__ == "__main__":
    index_directory(sys.argv[1] if len(sys.argv) > 1 else "docs")
