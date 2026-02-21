import os
import logging
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class RagEngine:
    """Handles retrieval augmented generation logic using Azure services."""

    _SCORE_THRESHOLD = 0.01

    def __init__(self):
        """Initialize Azure clients for Search and OpenAI."""
        self.credential = DefaultAzureCredential()
        self._embedding_cache: dict = {}
        
        self.azure_search_endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        self.azure_search_index_name = "bawn-mystery-index"
        self.search_client = SearchClient(
            endpoint=self.azure_search_endpoint, 
            index_name=self.azure_search_index_name, 
            credential=self.credential
        )

        self.azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        self.openai_client = AzureOpenAI(
            azure_endpoint=self.azure_openai_endpoint,
            azure_ad_token_provider=get_bearer_token_provider(self.credential, "https://cognitiveservices.azure.com/.default"),
            api_version="2024-02-01"
        )
        self.chat_model_deployment_name = "gpt-35-turbo"
        self.embedding_model_deployment_name = "text-embedding-ada-002"

    def health_check(self):
        """Verify search service connectivity by fetching document count."""
        self.search_client.get_document_count()

    def get_text_embedding(self, text_to_embed):
        """Return cached or freshly generated vector embedding."""
        if text_to_embed not in self._embedding_cache:
            response = self.openai_client.embeddings.create(
                input=text_to_embed,
                model=self.embedding_model_deployment_name
            )
            self._embedding_cache[text_to_embed] = response.data[0].embedding
        return self._embedding_cache[text_to_embed]

    def ask_question(self, user_question):
        """Retrieve context and generate answer for the user question."""
        question_embedding_vector = self.get_text_embedding(user_question)

        search_results = self.search_client.search(
            search_text=user_question,
            vector_queries=[VectorizedQuery(vector=question_embedding_vector, k_nearest_neighbors=3, fields="vector")],
            select=["content", "source"],
            top=3
        )

        retrieved_context_list = [
            f"Source: {r['source']}\nContent: {r['content']}"
            for r in search_results
            if r["@search.score"] >= self._SCORE_THRESHOLD
        ]
        logger.info("question=%r chunks=%d", user_question, len(retrieved_context_list))
        combined_context_string = "\n\n".join(retrieved_context_list)

        system_instruction_prompt = "You are a detective assistant. Use the provided context to answer the user's question about Mr. Bawn's mysteries. If you don't know, say so."
        user_query_prompt = f"Context:\n{combined_context_string}\n\nQuestion: {user_question}"

        chat_completion_response = self.openai_client.chat.completions.create(
            model=self.chat_model_deployment_name,
            messages=[
                {"role": "system", "content": system_instruction_prompt},
                {"role": "user", "content": user_query_prompt}
            ]
        )

        return chat_completion_response.choices[0].message.content, combined_context_string
