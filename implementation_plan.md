# Implementation Plan - Azure RAG App ("Toy" Scale)

## User Review Required
> [!IMPORTANT]
> **Infrastructure**: Manual configuration via Azure Portal. No IaC (Bicep/Terraform).
> **Language**: Python (FastAPI) for the Web App and Python (Azure Functions) for the Ingestion Worker.

## Proposed Changes

### Project Structure (Updated)
```text
.
├── src/
│   ├── webapp/             # FastAPI RAG Backend
│   │   ├── app.py          # Main entry point
│   │   ├── rag_engine.py   # Retrieval logic
│   │   └── templates/      # Simple HTML UI
│   ├── ingestion/          # Azure Function (Event Ingestion)
│   │   ├── function_app.py # Blob Trigger/Event Grid Trigger
│   │   └── indexer.py      # PDF/Text parsing & Vector push
├── docs/                   # (Existing) The mystery files
```

### [Infrastructure] (Manual via Portal)
Instead of code, we will manually create:
1.  **Resource Group**: `rg-bawn-rag`
2.  **Storage Account**: `st{name}` + Container `documents`
3.  **AI Search**: `search-{name}` (Basic/Free)
4.  **OpenAI**: `openai-{name}` (Deployments: `gpt-35-turbo`, `text-embedding-ada-002`)
5.  **App Service**: `app-{name}` (Linux/Python)
6.  **Function App**: `func-{name}` (consumption or app service plan)
7.  **Event Grid**: System Topic on Storage -> Function Subscription.
8.  **Identity**: Enable System Assisted Identity on Web App & Function. Grant RBAC roles manually.

### [Application Code] (Python)
#### [NEW] [src/webapp/app.py](file:///home/aifi/Projects/azure_rag_test/src/webapp/app.py)
- FastAPI app.
- Endpoint POST `/chat`: Accepts user query, runs RAG.
- Uses `azure-identity` (DefaultAzureCredential) for all auth.

#### [NEW] [src/ingestion/function_app.py](file:///home/aifi/Projects/azure_rag_test/src/ingestion/function_app.py)
- Azure Function V2 (Python).
- Trigger: Event Grid (Blob Created).
- Logic: Read Blob -> Split Text -> Embed -> Push to AI Search.

## Verification Plan

### Automated Tests
- **Unit Tests**: Test text splitter and prompt construction.
- **Linting**: Run `flake8` or `ruff` on Python code.
- **Bicep Build**: Run `az bicep build` to verify template syntax.

### Manual Verification
- **App Service Configuration**:
    - Manually set Env Vars: `AZURE_SEARCH_ENDPOINT`, `AZURE_OPENAI_ENDPOINT`, `STORAGE_ACCOUNT_NAME`.
- **RAG Flow**:
    1. Upload `docs/bawn_tokyo.txt` to Storage (Portal/Storage Explorer).
    2. Verify Indexer logs (Function Monitor).
    3. Query Web App.
