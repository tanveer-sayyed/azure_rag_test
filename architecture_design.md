# Architecture Design & Assumptions: Azure RAG App ("Toy" Scale)

## 1. Assumptions

Before architecting the solution for the "Mr. Bawn" Mystery RAG application, we define the following assumptions. "Premature complexity is technical debt," but we must adhere to the "Architect Truths" of Azure.

*   **Business Context**: Internal Organizational Tool. This is not a public SaaS. It serves authenticated users within the organization (Tenant).
*   **Data Classification**: "Confidential". The mystery documents (8 text files currently) contain sensitive case details. Security must be "Identity-First".
*   **Scale**: "Toy" scale currently (low traffic, small dataset), but the *Architecture* must be scalable. We will prioritize **Operational Simplicity** over infinite scale, but use patterns that *allow* scale (e.g., Event-Driven Ingestion) without refactoring the core.
*   **Constraints**: "No code has been written." We start with a clean slate.
*   **Operational Model**: The development team acts as the "Application Team". We assume a "Platform Team" exists (conceptually) that handles the Landing Zone, or we simulate those boundaries.

## 2. Architectural Decisions & The "Why"

We analyze each aspect of the system against the Azure Reference principles.

### A. Landing Zone (The Organizational Boundary)
**Decision**: Deploy to a dedicated Resource Group (e.g., `rg-bawn-rag-dev`) within a shared "Non-Prod" Subscription.
*   **Why**:
    *   *Reference*: "Subscriptions are billing + policy + blast-radius units... Start shared, split only when risk or scale demands it."
    *   *Rationale*: Creating a new subscription for a "Toy" app is an anti-pattern ("One Subscription Per App fails at scale"). A Resource Group handles the lifecycle boundary effectively for this size.

### B. Identity (The Control Plane)
**Decision**: Use **Microsoft Entra ID (Azure AD)** for all authentication. **Managed Identities** for compute-to-data access.
*   **Why**:
    *   *Reference*: "Azure Is Identity-First... Secrets are eliminated via managed identity."
    *   *Rationale*: We will strictly ban connection strings and API keys in code.
    *   *Implementation*:
        *   **Users**: Authenticate via App Service Easy Auth (Entra ID).
        *   **App Service**: Uses System-Assigned Managed Identity to talk to Blob Storage (Data) and AI Search/OpenAI.
        *   **Role-Based Access Control (RBAC)**: Assignments (e.g., "Storage Blob Data Reader") replace keys.

### C. Networking (Intent, Not Wiring)
**Decision**: Public Endpoint for App Service (Zero Trust enforced via Identity). Use Service Endpoints for Storage/DB strictly if required by policy, otherwise rely on Identity.
*   **Why**:
    *   *Reference*: "Public endpoint ≠ public access (because RBAC is already in place)... Zero trust beats flat networks."
    *   *Rationale*: A full Hub-and-Spoke with Private Links ($10/endpoint/month) creates "Premature Complexity" and cost for a toy app.
    *   *Security*: We rely on "Identity as the Perimeter". The app is public on the internet, but *inaccessible* without a valid Entra ID token.

### D. Compute (Cost, Ops, and RISK)
**Decision**: **Azure App Service (Linux Plan)**.
*   **Why**:
    *   *Reference*: "App Service is boring — and boring is good... 60% of AKS clusters should not exist!"
    *   *Rationale*: This is a standard web API/UI. We need fast time-to-market. We do not need the cognitive load of Kubernetes for 8 text files. VMs are rejected due to "OS patching forever."
    *   *Scaling*: App Service can scale out if the mystery goes viral.

### E. Data (Contract, Not Service)
**Decision**:
1.  **Binary Objects**: **Azure Blob Storage** for the raw text files (`docs/`).
    *   *Why*: "Blob storage is the only option (for documents...)."
2.  **Transactional/Search**: **Azure AI Search** (Vector Store) + **Azure OpenAI** (LLM).
    *   *Why*: "Data choices outlive applications." We need a specialized contract for vector retrieval.
3.  **App State**: **Cosmos DB** (Serverless) for Chat History (if needed).
    *   *Why*: "Global distribution" (overkill) but "Elastic scale" (good). Actually, for a *Toy*, simple Table Storage or SQL might suffice, but Cosmos Serverless fits the "Modern" pattern better. *Decision: Keep it simple. If "Toy" has no history, no DB needed yet. If history needed, Cosmos Serverless.*

### F. Integration (Event-Driven)
**Decision**: **Event Grid** attached to Blob Storage to trigger ingestion.
*   **Why**:
    *   *Reference*: "Modern Azure apps are event-driven... Async buys resilience."
    *   *Rationale*: When a user (or Mr. Bawn) uploads a new case file to Blob, distinct Code (Azure Function or Logic App) should handle the embedding/indexing. The Web App should NOT do this synchronously (Blocking the uploader).
    *   *Pattern*: Upload -> Blob Created Event -> Event Grid -> Ingestion Handler -> Vector Index. This decouples "Saving the file" from "Processing the AI".

### G. Security (Before Deployment)
**Decision**: Define **Azure Policies** (conceptually) and use **Infrastructure as Code** (Bicep).
*   **Why**:
    *   *Reference*: "Compliance is a by-product of architecture... Security After Deployment → Creates permanent exceptions."
    *   *Rationale*: Even if we don't deploy Policy definitions today, we write the Bicep templates to be compliant by default (e.g., "HTTPS Only", "TLS 1.2", "Managed Identity Only").

### H. Operations (Cost & Observability)
**Decision**: Enable **Application Insights** and **Log Analytics**.
*   **Why**:
    *   *Reference*: "If it’s not logged, it didn’t happen... Observability answers: What is slow?"
    *   *Rationale*: Essential for debugging the RAG pipeline (e.g., "Why did the LLM give a wrong answer?" -> Trace the retrieval correlation ID).

---
## Summary of "Toy" Architecture
*   **Frontend/API**: App Service (Linux)
*   **Auth**: Entra ID
*   **Storage**: Blob (Docs) + AI Search (Vectors)
*   **Async Processing**: Event Grid
*   **Ops**: App Insights

This architecture respects the "Consultant Currency" without incurring the massive overhead of a full "Hub-and-Spoke + AKS" deployment, which would be architectural overreach for this use case.
