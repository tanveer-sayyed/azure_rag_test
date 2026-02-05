import os
import logging
from azure.identity import DefaultAzureCredential
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

class Indexer:
    def __init__(self):
        self.credential = DefaultAzureCredential()
        
        # Env vars
        self.storage_account_name = os.environ["STORAGE_ACCOUNT_NAME"]
        self.search_endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        self.openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        self.index_name = "bawn-mystery-index"

        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{self.storage_account_name}.blob.core.windows.net", 
            credential=self.credential
        )
        
        self.index_client = SearchIndexClient(endpoint=self.search_endpoint, credential=self.credential)
        self.search_client = SearchClient(endpoint=self.search_endpoint, index_name=self.index_name, credential=self.credential)
        
        self.openai_client = AzureOpenAI(
            azure_endpoint=self.openai_endpoint,
            azure_ad_token_provider=self.credential.get_token("https://cognitiveservices.azure.com/.default").token,
            api_version="2023-05-15"
        )
        self.embedding_deployment = "text-embedding-ada-002"

    def ensure_index(self):
        if self.index_name not in self.index_client.list_index_names():
            logging.info(f"Creating index {self.index_name}...")
            # Define Index
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SimpleField(name="source", type=SearchFieldDataType.String),
                SearchField(name="vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                            searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile")
            ]
            
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(name="myHnsw")
                ],
                profiles=[
                    VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")
                ]
            )

            index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)
            self.index_client.create_index(index)
            logging.info("Index created.")

    def get_embedding(self, text):
        response = self.openai_client.embeddings.create(
            input=text,
            model=self.embedding_deployment
        )
        return response.data[0].embedding

    def process_blob(self, blob_url):
        # blob_url format: https://<account>.blob.core.windows.net/<container>/<blob>
        # Parse container and blob name
        parts = blob_url.split("/")
        container_name = parts[-2]
        blob_name = parts[-1]

        logging.info(f"Processing blob: {blob_name} from {container_name}")
        
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        download_stream = blob_client.download_blob()
        content = download_stream.readall().decode('utf-8')

        # Ensure index exists
        self.ensure_index()

        # Simple chunking (per line for now, or per paragraph)
        # For Mr. Bawn docs (100 lines), getting the whole text + embedding might overflow if too big, 
        # but 100 lines is likely < 8k tokens. Let's do a simple sliding window or just block.
        # Let's chunk by paragraphs (double newline).
        chunks = content.split("\n\n")
        
        documents = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            
            vector = self.get_embedding(chunk)
            doc_id = f"{blob_name}-{i}".replace(".txt", "").replace("_", "-") # Simple ID sanitization
            
            documents.append({
                "id": doc_id,
                "content": chunk,
                "source": blob_name,
                "vector": vector
            })
            
            if len(documents) >= 10: # Batch upload
                self.search_client.upload_documents(documents)
                documents = []

        if documents:
            self.search_client.upload_documents(documents)
        
        logging.info(f"Indexed {blob_name} successfully.")
