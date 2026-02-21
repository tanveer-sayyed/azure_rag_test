import os
import logging
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.storage.blob import BlobServiceClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile
)
from openai import AzureOpenAI

class DocumentIndexer:
    """Handles document indexing from Blob Storage to Azure AI Search."""

    def __init__(self):
        """Initialize Azure clients for Storage, Search, and OpenAI."""
        self.credential = DefaultAzureCredential()
        
        self.storage_account_name = os.environ["STORAGE_ACCOUNT_NAME"]
        self.azure_search_endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        self.azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        self.search_index_name = "bawn-mystery-index"

        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{self.storage_account_name}.blob.core.windows.net", 
            credential=self.credential
        )
        
        self.search_index_client = SearchIndexClient(endpoint=self.azure_search_endpoint, credential=self.credential)
        self.search_document_client = SearchClient(endpoint=self.azure_search_endpoint, index_name=self.search_index_name, credential=self.credential)
        
        self.openai_client = AzureOpenAI(
            azure_endpoint=self.azure_openai_endpoint,
            azure_ad_token_provider=get_bearer_token_provider(self.credential, "https://cognitiveservices.azure.com/.default"),
            api_version="2024-02-01"
        )
        self.embedding_model_deployment_name = "text-embedding-ada-002"
        self.ensure_search_index_exists()

    def ensure_search_index_exists(self):
        """Create the Azure AI Search index if it does not exist."""
        if self.search_index_name not in self.search_index_client.list_index_names():
            search_fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SimpleField(name="source", type=SearchFieldDataType.String),
                SearchField(name="vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                            searchable=True, vector_search_dimensions=1536, vector_search_profile_name="hnsw_vector_profile")
            ]
            
            vector_search_config = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(name="hnsw_algo_config")
                ],
                profiles=[
                    VectorSearchProfile(name="hnsw_vector_profile", algorithm_configuration_name="hnsw_algo_config")
                ]
            )

            new_search_index = SearchIndex(name=self.search_index_name, fields=search_fields, vector_search=vector_search_config)
            self.search_index_client.create_index(new_search_index)

    def generate_batch_embeddings(self, text_list):
        """Generate embeddings for all texts in a single API call."""
        response = self.openai_client.embeddings.create(
            input=text_list,
            model=self.embedding_model_deployment_name
        )
        return [item.embedding for item in response.data]

    def process_blob_document(self, blob_resource_url):
        """Download blob, chunk text, generate embeddings, and upload to search index."""
        url_parts_list = blob_resource_url.split("/")
        container_name_string = url_parts_list[-2]
        blob_name_string = url_parts_list[-1]

        blob_client_instance = self.blob_service_client.get_blob_client(container=container_name_string, blob=blob_name_string)
        blob_download_stream = blob_client_instance.download_blob()
        blob_text_content = blob_download_stream.readall().decode('utf-8')

        indexed_chunks = [
            (i, chunk) for i, chunk in enumerate(blob_text_content.split("\n\n"))
            if chunk.strip()
        ]
        chunk_vectors = self.generate_batch_embeddings([chunk for _, chunk in indexed_chunks])

        document_batch_list = []
        for (chunk_index, text_chunk), vector in zip(indexed_chunks, chunk_vectors):
            document_unique_id = f"{blob_name_string}-{chunk_index}".replace(".txt", "").replace("_", "-")
            document_batch_list.append({
                "id": document_unique_id,
                "content": text_chunk,
                "source": blob_name_string,
                "vector": vector
            })
            if len(document_batch_list) >= 10:
                self.search_document_client.upload_documents(document_batch_list)
                document_batch_list = []

        if document_batch_list:
            self.search_document_client.upload_documents(document_batch_list)
