# Azure RAG App ("Toy" Scale) - Walkthrough (Manual Deployment)

I have implemented the code for the "Toy" RAG application. The infrastructure deployment is now manual via the Azure Portal.

## Architecture Recap
- **Frontend/API**: Python FastAPI (`src/webapp`).
- **Ingestion**: Azure Function (`src/ingestion`).
- **Data**: Azure Blob Storage + Azure AI Search.
- **AI**: Azure OpenAI.

## Deployment Steps (Manual)

### 1. Create Resources in Azure Portal
1.  **Resource Group**: Create `rg-bawn-rag`.
2.  **Storage Account**: Create `stbawnrag`.
    *   Create Container: `documents`.
3.  **Azure AI Search**: Create `search-bawn-rag`.
    *   Note the **Endpoint**.
4.  **Azure OpenAI**: Create `openai-bawn-rag`.
    *   Deploy Model: `gpt-35-turbo` (Version 0613 or newer).
    *   Deploy Model: `text-embedding-ada-002` (Version 2).
    *   Note the **Endpoint**.
5.  **App Service**: Create `app-bawn-rag` (Linux, Python 3.11).
    *   Enable **System Assigned Identity**.
6.  **Function App**: Create `func-bawn-rag` (Linux, Python 3.11, Consumer or App Service Plan).
    *   Enable **System Assigned Identity**.

### 2. Configure Permissions (RBAC)
Go to the respective resources and add **Role Assignments** for *both* the App Service Identity and Function App Identity (where applicable):

| Resource | Role | Assignee |
| :--- | :--- | :--- |
| **Storage Account** | `Storage Blob Data Reader` | Web App |
| **Storage Account** | `Storage Blob Data Owner` | Function App (Needs Owner/Contributor for triggers) |
| **Storage Account** | `Storage Queue Data Contributor`| Function App |
| **AI Search** | `Search Index Data Reader` | Web App |
| **AI Search** | `Search Index Data Contributor` | Function App |
| **Azure OpenAI** | `Cognitive Services OpenAI User` | Web App & Function App |

### 3. Configure Environment Variables
Add these to **App Settings** (Configuration) in App Service and Function App:

| Setting | Value |
| :--- | :--- |
| `AZURE_SEARCH_ENDPOINT` | `https://search-bawn-rag.search.windows.net` |
| `AZURE_OPENAI_ENDPOINT` | `https://openai-bawn-rag.openai.azure.com/` |
| `STORAGE_ACCOUNT_NAME` | `stbawnrag` |

### 4. Deploy Code
1.  **Web App**: Zip `src/webapp/` and deploy using CLI or VS Code.
    ```bash
    cd src/webapp && zip -r webapp.zip .
    az webapp deploy --resource-group rg-bawn-rag --name app-bawn-rag --src-path webapp.zip --type zip
    ```
2.  **Function App**: Deploy `src/ingestion`.
    ```bash
    cd src/ingestion
    func azure functionapp publish func-bawn-rag --python
    ```

### 5. Setup Event Grid
1.  Go to Storage Account -> **Events**.
2.  Create **Event Subscription**.
3.  Endpoint Type: **Azure Function**.
4.  Select your `func-bawn-rag` and the `IngestBlob` function.
5.  Filter: Subject Begins With `/blobServices/default/containers/documents`.

### 6. Verify
1.  Upload a file to `documents` container.
2.  Check Function Logs.
3.  Visit Web App URL.
