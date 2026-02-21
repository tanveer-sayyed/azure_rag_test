import os
import logging
import weaviate
import weaviate.classes.config as wvc_config
from weaviate.classes.query import MetadataQuery
from sentence_transformers import SentenceTransformer
import ollama as ollama_client

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_COLLECTION = "BawnMystery"
_DISTANCE_THRESHOLD = 0.5


class RagEngine:
    """Handles retrieval augmented generation logic using local services."""

    def __init__(self):
        """Initialize sentence-transformer, Weaviate client, and Ollama config."""
        self._encoder = SentenceTransformer(_EMBEDDING_MODEL)
        self._embedding_cache: dict = {}

        weaviate_url = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
        url_no_scheme = weaviate_url.replace("https://", "").replace("http://", "")
        weaviate_host, weaviate_port = (url_no_scheme.rsplit(":", 1) + ["8080"])[:2]
        self._weaviate = weaviate.connect_to_local(host=weaviate_host, port=int(weaviate_port))

        if not self._weaviate.collections.exists(_COLLECTION):
            self._weaviate.collections.create(
                name=_COLLECTION,
                vectorizer_config=wvc_config.Configure.Vectorizer.none(),
                properties=[
                    wvc_config.Property(name="content", data_type=wvc_config.DataType.TEXT),
                    wvc_config.Property(name="source", data_type=wvc_config.DataType.TEXT),
                ],
            )

        self._ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

    def health_check(self):
        """Verify Weaviate is reachable."""
        if not self._weaviate.is_ready():
            raise RuntimeError("Weaviate is not ready")

    def get_text_embedding(self, text_to_embed):
        """Return cached or freshly generated sentence-transformer embedding."""
        if text_to_embed not in self._embedding_cache:
            self._embedding_cache[text_to_embed] = self._encoder.encode(text_to_embed).tolist()
        return self._embedding_cache[text_to_embed]

    def ask_question(self, user_question):
        """Retrieve context and generate answer for the user question."""
        question_vector = self.get_text_embedding(user_question)

        collection = self._weaviate.collections.get(_COLLECTION)
        results = collection.query.near_vector(
            near_vector=question_vector,
            limit=3,
            return_metadata=MetadataQuery(distance=True),
        )

        retrieved_context_list = [
            f"Source: {obj.properties['source']}\nContent: {obj.properties['content']}"
            for obj in results.objects
            if obj.metadata.distance < _DISTANCE_THRESHOLD
        ]
        logger.info("question=%r chunks=%d", user_question, len(retrieved_context_list))
        combined_context = "\n\n".join(retrieved_context_list)

        system_prompt = "You are a detective assistant. Use the provided context to answer the user's question about Mr. Bawn's mysteries. If you don't know, say so."
        user_prompt = f"Context:\n{combined_context}\n\nQuestion: {user_question}"

        response = ollama_client.chat(
            model=self._ollama_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        return response.message.content, combined_context
