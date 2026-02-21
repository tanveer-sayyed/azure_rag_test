import os
import logging
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import weaviate
import weaviate.classes.config as wvc_config
from weaviate.util import generate_uuid5
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_COLLECTION = "BawnMystery"


class DocumentIndexer:
    """Handles document indexing from Azure Blob Storage to Weaviate."""

    def __init__(self):
        """Initialize blob client, sentence-transformer, and Weaviate client."""
        self.credential = DefaultAzureCredential()
        self.storage_account_name = os.environ["STORAGE_ACCOUNT_NAME"]
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{self.storage_account_name}.blob.core.windows.net",
            credential=self.credential,
        )

        self._encoder = SentenceTransformer(_EMBEDDING_MODEL)

        weaviate_url = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
        url_no_scheme = weaviate_url.replace("https://", "").replace("http://", "")
        weaviate_host, weaviate_port = (url_no_scheme.rsplit(":", 1) + ["8080"])[:2]
        self._weaviate = weaviate.connect_to_local(host=weaviate_host, port=int(weaviate_port))
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Create Weaviate collection if it does not exist."""
        if not self._weaviate.collections.exists(_COLLECTION):
            self._weaviate.collections.create(
                name=_COLLECTION,
                vectorizer_config=wvc_config.Configure.Vectorizer.none(),
                properties=[
                    wvc_config.Property(name="content", data_type=wvc_config.DataType.TEXT),
                    wvc_config.Property(name="source", data_type=wvc_config.DataType.TEXT),
                ],
            )

    def generate_batch_embeddings(self, text_list):
        """Generate embeddings for all texts in a single encode call."""
        return self._encoder.encode(text_list).tolist()

    def process_blob_document(self, blob_resource_url):
        """Download blob, chunk text, generate embeddings, and upload to Weaviate."""
        url_parts = blob_resource_url.split("/")
        container_name = url_parts[-2]
        blob_name = url_parts[-1]

        blob_text = (
            self.blob_service_client
            .get_blob_client(container=container_name, blob=blob_name)
            .download_blob()
            .readall()
            .decode("utf-8")
        )

        indexed_chunks = [
            (i, chunk) for i, chunk in enumerate(blob_text.split("\n\n"))
            if chunk.strip()
        ]
        vectors = self.generate_batch_embeddings([chunk for _, chunk in indexed_chunks])

        collection = self._weaviate.collections.get(_COLLECTION)
        with collection.batch.dynamic() as batch:
            for (chunk_index, text_chunk), vector in zip(indexed_chunks, vectors):
                batch.add_object(
                    properties={"content": text_chunk, "source": blob_name},
                    vector=vector,
                    uuid=generate_uuid5(f"{blob_name}-{chunk_index}"),
                )
        logger.info("indexed %s (%d chunks)", blob_name, len(indexed_chunks))
