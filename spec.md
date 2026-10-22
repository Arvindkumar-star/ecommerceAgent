# Project Upgrade: Existing E-commerce Agent → Real Multi-Company AI Support Platform

## 1. Your role

Act as a senior AI engineer, Python developer, LangChain/LangGraph specialist, RAG engineer, backend architect, and professional UI/UX designer.

I already have an E-commerce Customer Support Agent built using Python, LangChain, and LangGraph.

My existing project includes an agent workflow with shared state, planning and tool execution, conditional routing, a tool loop, and final response generation. It also includes or is being extended with semantic caching, agent metrics, safety guardrails, and retrieval functionality.

Your task is to upgrade my existing codebase into a **real, configurable, multi-company AI customer-support and RAG platform**.

This is an enhancement of my existing project, not a request to create a completely new application.

## 2. Non-negotiable requirements

### A. Preserve the existing project

Before modifying anything:

1. Inspect the complete repository, folder structure, dependencies, configuration, and execution flow.
2. Identify the current agent state, LangGraph nodes, tools, retrieval pipeline, vector store, cache, metrics, guardrails, backend, and frontend.
3. Identify exactly where dummy orders, hardcoded policies, fake customer records, and mock business responses are used.
4. Reuse working code, functions, classes, graph nodes, and dependencies wherever possible.
5. Do not rewrite the entire project or replace the existing agent architecture unnecessarily.
6. Modify only the components that must change to implement the requirements.
7. Preserve working semantic caching, metrics, guardrails, and agent logic unless a specific modification is required.
8. If an architectural change is necessary, explain why and keep the change as small as possible.
9. If a frontend already exists, improve it rather than creating a duplicate frontend.

### B. Absolutely no local demo data

**The application must not contain or use local demo data.**

Do not create or retain any application-facing:
- Demo mode or demo-data mode
- Fake orders or customer records
- Fake inventory or product availability
- Hardcoded company policies presented as real information
- Sample conversations presented as real user activity
- Fabricated analytics or dashboard statistics
- Mock business responses as a production fallback
- Automatically generated sample company documents or business records
- Silent fallbacks to hardcoded data when an integration fails

Remove obsolete dummy-data files, imports, seed scripts, sample-data generators, and fallback branches when they are no longer needed.

Do not simply hide dummy data in the UI while leaving the application dependent on it in the backend.

Search the complete repository for these patterns and remove the obsolete application paths safely.

Automated tests may use isolated test fixtures and mocks. These must remain strictly within the test environment and must never be served to actual users or used as a production fallback.

### C. Real data only

Use:
- Real company documents uploaded by authorized company users for RAG.
- Real, authorized databases or APIs for current order information.
- Real, authorized inventory sources for stock information.
- Actual stored application records for dashboard statistics and analytics.
- Verified retrieved source documents for citations.

If a required source is unavailable, report the limitation explicitly. Never invent an answer to make the application appear functional.

Do not claim that an integration is operational until it has been configured and successfully tested.

## 3. Final product vision

Build a reusable platform that multiple companies can configure for their own customer-support requirements.

Each company should be able to upload its own documents, maintain its own knowledge base, and receive answers grounded in its own data.

Supported document formats should include PDF, DOCX, TXT, and CSV, subject to reliable parser support.

Examples of company documents:
- Return and refund policies
- Shipping and delivery policies
- Product manuals
- Product catalogues
- FAQs
- Warranty documents
- Customer-support guidelines

The system must distinguish between:

1. Information retrieved from uploaded company documents.
2. Current operational data retrieved from authorized external systems.
3. Information that cannot be verified from the available sources.

When evidence is insufficient, the system must explicitly state that it cannot verify the answer.

## 4. Implementation roadmap

Implement the following phases in order, making minimal changes to the existing project.

### Phase 1: Inspect and prepare the existing codebase

Inspect the entire repository before editing.

Identify:
- Current agent architecture and entry points
- Shared agent state and graph nodes
- Existing tool definitions and tool execution
- Dummy order and policy data
- Existing RAG implementation
- Embedding model and vector store
- Semantic cache and cache invalidation
- Metrics and safety guardrails
- Existing backend endpoints and frontend pages
- Existing database and external integrations
- Existing tests and environment configuration

Then:
1. Provide a concise implementation plan.
2. Identify files that require modification.
3. Remove obsolete dummy-data dependencies safely.
4. Continue with implementation rather than stopping after the plan.

Do not delete or rewrite unrelated working code.

### Phase 2: Company document ingestion and RAG

Implement or extend the document-ingestion pipeline.

Required workflow:

1. An authenticated company user uploads a document.
2. The backend validates its format, size, and access permissions.
3. Text is extracted from the document.
4. The text is divided into suitable chunks.
5. Embeddings are generated using the existing embedding configuration where possible.
6. Chunks are stored in the configured vector store.
7. Source metadata is retained.
8. The indexed content becomes available for retrieval.

Every chunk should retain relevant metadata:
- `company_id`
- `document_id`
- `filename`
- `page_number`, where available
- `chunk_id`
- Document version or ingestion timestamp

Use a suitable source-location field for formats without page numbers.

Implement or extend:

`retrieve_company_knowledge(company_id, query)`

Responsibilities:
- Retrieve relevant chunks from the correct company's knowledge base.
- Enforce company-level filtering on the backend.
- Return actual retrieved text and source metadata.
- Use configurable retrieval limits and relevance thresholds.
- Avoid returning irrelevant chunks merely to fill a result limit.
- Provide valid citations that refer to actual uploaded documents.

One reusable retrieval tool must work across all documents belonging to a company. Do not create one tool per document.

If a company has not uploaded any documents, show an empty knowledge-base state. Do not insert example documents automatically.

If the vector store or embedding service is not configured, explain what configuration is required rather than using an alternative local demo store.

### Phase 3: Replace hardcoded business data with real integrations

Inspect the existing dummy order database, customer records, inventory records, and hardcoded policy information.

Remove the dummy business-data dependencies from application workflows.

Implement or extend the following tools.

#### Tool 1: `get_order_details(order_id)`

- Fetch order information from an authorized database or configured e-commerce API.
- Verify that the authenticated customer is authorized to access the requested order.
- Return only the required order information.
- Never invent an order, status, payment, customer, or delivery date.
- Return an explicit unavailable or integration-error status when the real source cannot be queried.

#### Tool 2: `check_inventory(product_id)`

- Retrieve current stock from a configured inventory source.
- Report freshness or the last-updated timestamp when available.
- Never fabricate stock quantities.
- Report when the integration is not configured or the information cannot be retrieved.

#### Tool 3: `check_return_eligibility(order_id)`

- Obtain verified order details.
- Retrieve the applicable company's current return policy.
- Apply explicit eligibility rules using verified order information and policy parameters.
- Distinguish between eligible, ineligible, and unable to determine.
- Explain the decision and cite the supporting policy document where available.
- Never invent a policy, return window, purchase date, or delivery status.

Business rules may remain in application code where appropriate, but company-specific policy values must come from verified company sources rather than arbitrary hardcoded assumptions.

#### Integration architecture

Do not assume that a particular e-commerce API or database exists.

First inspect the existing integrations. If no real integration is configured:
- Create a clean adapter interface.
- Document the required connection settings.
- Provide a secure configuration path for the company.
- Display the integration as not configured until a real connection is established and verified.

Do not create fake data to make the integration appear connected.

Keep the agent workflow independent of any particular company's backend so companies can connect supported systems without requiring the agent to be rewritten.

Do not implement `create_return_request()` yet. It can be added later after authentication, authorization, eligibility checks, and explicit customer confirmation are ready.

### Phase 4: Multi-company isolation and document management

Make the knowledge base company-aware.

Implement:
- Verified company identity and access control
- Document ownership
- Company-scoped retrieval
- Document listing and status tracking
- Document deletion
- Document updates and re-ingestion
- Version management
- Cleanup of obsolete indexed chunks

Security requirements:
- Never trust a user-supplied `company_id` as proof of authorization.
- Resolve company identity through an authenticated session or verified backend context.
- Enforce tenant filters server-side.
- Prevent one company from retrieving another company's documents.
- Prevent unauthorized access through document IDs.
- Do not expose private company documents through public URLs.
- Ensure document deletion removes its indexed chunks and related cached answers.
- Do not treat an upload as indexed until ingestion succeeds.

If authentication is missing, implement an appropriate authentication boundary before claiming that multi-company isolation is production-ready.

### Phase 5: Integrate with the existing LangGraph agent

Preserve the existing graph structure, shared state, planning, tool execution, conditional routing, and final response generation wherever possible.

Connect these tools to the existing agent:

- `retrieve_company_knowledge`
- `get_order_details`
- `check_inventory`
- `check_return_eligibility`

Avoid duplicate tools or unnecessary graph rewrites.

Expected behavior:

**Question:** "What is your return policy?"

- Retrieve the current company's relevant policy.
- Generate an answer grounded in retrieved evidence.
- Provide citations to the actual source.

**Question:** "Where is my order?"

- Ask for an order ID if needed.
- Verify customer authorization.
- Query the configured live order source.
- Never guess the order status.

**Question:** "Is this product in stock?"

- Query the real inventory source.
- Report verified stock information and freshness when available.

**Question:** "Can I return my delivered order?"

- Verify the order.
- Retrieve the applicable policy.
- Evaluate eligibility.
- Explain the result using actual order information and policy evidence.

If an integration is unavailable, do not substitute dummy results.

If documents are missing, irrelevant, outdated, or conflicting, communicate that limitation clearly.

### Phase 6: Preserve caching, metrics, and safety guardrails

Reuse the existing implementations wherever possible.

#### Semantic cache

- Include company identity and relevant authorization scope in cache keys.
- Prevent cross-company cache leakage.
- Include relevant query and configuration context.
- Invalidate or version entries when source documents change.
- Avoid unsafe caching of sensitive customer-specific responses.
- Apply suitable freshness rules to live order and inventory responses.
- Never return cached information from a different company or unauthorized user.

#### Agent metrics

Track actual observed data where available:
- Retrieval latency
- Tool latency
- Total response time
- Errors and failed integrations
- Cache hits and misses
- Token usage and estimated model cost, if supported

Do not populate analytics with invented values. Avoid logging unnecessary personal or confidential information.

#### Safety guardrails

- Preserve step limits and cost controls.
- Validate tool inputs and outputs.
- Mask sensitive personal information in logs where appropriate.
- Validate citations against retrieved sources.
- Treat uploaded documents as untrusted content, not instructions that override system rules.
- Handle invalid inputs, missing configuration, and external-service failures safely.

### Phase 7: Build a premium, functional UI

Inspect the existing frontend first. Improve it rather than creating a second frontend.

If no frontend exists, choose an appropriate framework after inspecting the repository. Prefer a modern React-based frontend if compatible with the existing backend.

Design a polished commercial SaaS application with:
- Clean layouts and professional typography
- Consistent spacing and reusable components
- Neutral surfaces with restrained indigo or violet accents
- Accessible contrast
- Responsive desktop, tablet, and mobile layouts
- Subtle animations
- Consistent buttons, tables, icons, forms, and status indicators
- Useful loading, error, and empty states

Avoid excessive gradients, decorative cards, fake charts, and unnecessary animations.

#### A. Main dashboard layout

Use a responsive sidebar and main content area.

Suggested navigation:
- Overview
- AI Support Chat
- Knowledge Base
- Orders & Inventory
- Analytics
- Settings

Only show implemented functionality.

If an integration is missing, show a clear setup state. Do not fill the page with sample orders or fabricated information.

#### B. Overview dashboard

Display only real application data, such as:
- Actual number of indexed documents
- Real recent uploads
- Actual conversations, if stored
- Measured retrieval performance
- Actual tool failures
- Measured latency and cache performance

If no records exist, show an empty state such as "No activity yet."

If an integration is unavailable, show "Not configured." Never invent a number to make the dashboard look populated.

#### C. AI Support Chat

Make this the main user-facing feature.

Include:
- Clean message layout
- Clear user and assistant message styling
- Empty state with suggested questions that do not imply that fake business data exists
- Message input and send button
- Enter-to-send and Shift+Enter for a new line
- Loading and error states
- Conversation history when actually supported
- New-conversation action
- Readable Markdown rendering
- Responsive layout

For RAG answers, provide an expandable source panel showing actual:
- Document filename
- Page or section, where available
- Relevant excerpt
- Relevance score, only when reliably available

Never fabricate citations.

Clearly distinguish:
- Answers grounded in company documents
- Results obtained from live business systems
- Unverified answers
- Missing or failed integrations

Do not expose stack traces, secrets, or internal exception details.

#### D. Knowledge Base

Provide:
- Drag-and-drop upload
- File picker
- Supported-format and file-size guidance
- Upload progress when available
- Document list
- File type and actual processing status
- Upload time and relevant metadata
- Search or filtering when useful
- Retry for failed ingestion
- Delete action with confirmation
- Helpful validation errors

When there are no documents, show a professional empty state explaining how to upload the first company document.

Never generate sample documents or display fake document records.

Show "Indexed" only after successful indexing.

#### E. Orders and Inventory

Display actual data only when the corresponding real integration is configured and authorized.

When no integration is configured:
- Show an integration setup page.
- Explain which connection is required.
- Do not display fake orders, inventory quantities, or product records.

#### F. Analytics

Display only metrics collected from real application activity.

Examples:
- Actual query count
- Actual tool usage
- Measured retrieval latency
- Measured response latency
- Actual cache-hit rate
- Actual error rate
- Estimated model cost when available

Show charts only when enough real records exist. Otherwise, show a meaningful empty state.

Never populate charts with invented numbers.

#### G. Settings and integrations

Provide configuration interfaces for supported features:
- Company information
- Model and embedding configuration
- Vector-store configuration
- E-commerce database or API
- Integration status
- Retrieval settings

Do not expose secret credentials to the browser, logs, or frontend responses.

Use secure backend configuration and environment variables. Do not invent credentials or claim a connection is working without verification.

### Phase 8: API, configuration, and reliability

Use the existing backend framework and conventions.

Ensure:
- Consistent request and response schemas
- Input validation
- Appropriate HTTP status codes
- Safe error messages
- File upload restrictions
- Timeouts for external services
- Useful server-side logging
- No accidental exposure of secrets

Do not introduce a new framework unnecessarily.

Update `.env.example` with required configuration variables, but never overwrite or print real secrets from `.env`.

When required services are not configured, fail clearly and safely. Do not silently fall back to local files, mock services, or hardcoded business data.

### Phase 9: Testing and verification

Write or extend automated tests for the existing and new functionality.

Verify at least:

1. Supported company documents can be uploaded and indexed.
2. Retrieval returns relevant chunks and valid source metadata.
3. Answers are grounded in uploaded policy documents.
4. Questions without supporting evidence do not produce invented answers.
5. One company cannot retrieve another company's documents.
6. Unauthorized customers cannot access another customer's orders.
7. Missing order integrations return explicit unavailable statuses.
8. Missing inventory integrations return explicit unavailable statuses.
9. Return eligibility handles missing and conflicting information safely.
10. Updating and deleting documents correctly updates the index and cache.
11. Cached answers cannot leak across company or user boundaries.
12. UI loading, empty, success, and error states work correctly.
13. Existing agent functionality remains intact.
14. No production application path depends on local demo data or mock business responses.

Mocks and fixtures may be used only in isolated automated tests. Do not expose them through application endpoints or production UI.

Run available tests, linting, and build commands. Fix regressions caused by the changes.

Report actual results. Never claim tests passed unless they were executed successfully.

### Phase 10: Documentation and final handover

Update the README with:
- Architecture overview
- Setup and dependency installation
- Environment configuration
- Backend and frontend startup commands
- Embedding model and vector-store setup
- Company document upload and indexing instructions
- Real business-integration setup
- Company isolation and security
- Testing instructions
- Known limitations and production-readiness gaps

At completion, report:
1. Implemented functionality
2. Files created, modified, and deleted
3. Dummy-data paths removed
4. Dependencies changed
5. Required environment variables
6. Commands to run the application
7. Tests actually executed and their results
8. Integrations still awaiting configuration
9. Known limitations and remaining work

## 5. Technical requirements

- Preserve the existing working architecture.
- Prefer minimal, targeted code changes.
- Use modular and maintainable code.
- Reuse existing abstractions.
- Avoid unnecessary dependencies.
- Use one reusable document retrieval tool per company-scoped knowledge workflow, not one tool per document.
- Keep document retrieval separate from live operational data.
- Enforce company isolation on the backend.
- Keep credentials out of the source code and frontend bundles.
- Do not add a demo mode or production mock-data fallback.
- Preserve regression coverage for existing functionality.

## 6. Implementation workflow

For each phase:

1. Inspect the relevant existing files.
2. Explain the minimal proposed changes.
3. Implement those changes.
4. Run relevant tests or verification commands.
5. Fix any regressions introduced.
6. Summarize what changed and what remains.

Do not replace the project with a new scaffold. Do not delete unrelated working code.

If a real external integration requires credentials, API access, or a service that is not available, implement its integration boundary and document the required configuration. Clearly mark it as unconfigured until a real connection is successfully verified.

**Start by inspecting my existing repository. Then implement the phases in order, preserving working code, removing local demo data from application workflows, and building a polished UI that uses real company data only.**