import os
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

class RagEngine:
    def __init__(self):
        self.credential = DefaultAzureCredential()
        
        self.search_endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        self.index_name = "bawn-mystery-index" # Assumed index name
        self.search_client = SearchClient(
            endpoint=self.search_endpoint, 
            index_name=self.index_name, 
            credential=self.credential
        )

        self.openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        self.openai_client = AzureOpenAI(
            azure_endpoint=self.openai_endpoint,
            azure_ad_token_provider=self.credential.get_token("https://cognitiveservices.azure.com/.default").token,
            api_version="2023-05-15"
        )
        self.deployment_id = "gpt-35-turbo"
        self.embedding_deployment = "text-embedding-ada-002"

    def get_embedding(self, text):
        response = self.openai_client.embeddings.create(
            input=text,
            model=self.embedding_deployment
        )
        return response.data[0].embedding

    def ask(self, question):
        # 1. Embed question
        vector = self.get_embedding(question)

        # 2. Retrieve relevant docs
        results = self.search_client.search(
            search_text=question,
            vector_queries=[VectorizedQuery(vector=vector, k_nearest_neighbors=3, fields="vector")],
            select=["content", "source"],
            top=3
        )

        context_parts = []
        for result in results:
            context_parts.append(f"Source: {result['source']}\nContent: {result['content']}")
        
        context = "\n\n".join(context_parts)

        # 3. Generate Answer
        system_prompt = "You are a detective assistant. Use the provided context to answer the user's question about Mr. Bawn's mysteries. If you don't know, say so."
        user_prompt = f"Context:\n{context}\n\nQuestion: {question}"

        response = self.openai_client.chat.completions.create(
            model=self.deployment_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content, context
