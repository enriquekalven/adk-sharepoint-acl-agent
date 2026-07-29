# 🔐 ADK SharePoint Knowledge Agent (Veer Muchandi ACL Pattern)

A production-ready **Google Cloud Agent Development Kit (ADK 2.x)** agent that securely queries enterprise SharePoint datastores via Google Cloud Discovery Engine.

This repository implements **Veer Muchandi's OAuth/ACL Token Propagation Pattern**, allowing custom ADK agents to inherit and enforce the calling user's native SharePoint Access Control Lists (ACLs) dynamically at query time.

---

## 🎯 Key Architectural Objectives & Features

1. **Native SharePoint ACL Enforcement**: Dynamically extracts the session-injected Azure AD OAuth token from `ToolContext.state[AUTH_NAME]` and passes it to Discovery Engine's REST API (`discoveryengine.googleapis.com`), ensuring users only see documents they are authorized to access.
2. **Connector Wall & `VertexAiSearchTool` Bypass**: Direct REST client implementation bypasses known product issues (GCP Issues #434712760, #483989453, #484437320) where `VertexAiSearchTool` defaults to Service Account (ADC) credentials.
3. **Hybrid Auth Fallback**: Automatically uses active session tokens in production environments, while falling back to local **Application Default Credentials (ADC)** during local developer testing.
4. **Production Hardening**:
   - **Token Expiry (HTTP 401)**: Returns a structured `AUTH_EXPIRED` signal prompting the user to refresh their session.
   - **Non-Blocking Timeouts**: HTTP request timeouts (`3.05s` connect / `10s` read) prevent thread starvation under concurrent load.
   - **API Gateway Attribution**: Includes `X-Goog-User-Project` headers for proper GCP quota/billing.
   - **Multi-Schema JSON Parsing**: Robust fallback parsing across `derivedStructData`, `structData`, and `document.name`.
5. **AlphaEvolve Reranking Suite (`ae_experiment/`)**: DeepMind-compliant 3-tier evolutionary search experiment package for optimizing search result relevance and context token compression.

---

## 📂 Directory Layout

```text
sharepoint_adk_agent/
├── README.md                  # Project documentation & execution guide
├── requirements.txt           # Python dependencies (google-adk, google-auth, requests)
├── agent.py                   # Core ADK RootAgent definition & modular system prompt
├── agent.yaml                 # Deployment manifest with authorizationConfig & Project Number
├── test_agent.py              # Automated 5-tier test suite
├── tools/
│   ├── __init__.py            # Tools package initializer
│   └── sharepoint_search.py   # Custom ADK tool with Veer ACL token propagation
└── ae_experiment/             # AlphaEvolve Optimization Suite
    ├── initial_program.py     # Seed program containing EVOLVE-BLOCK reranker
    ├── evaluator.py           # 3-Tier Evaluator (Validation, Verification, Evaluation)
    └── benchmark_data.json    # Search query ground-truth benchmark dataset
```

---

## ⚙️ Environment Configuration

Set the following environment variables (or define them in `agent.yaml`):

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `PROJECT_ID` | GCP Project ID | `your-gcp-project-id` |
| `PROJECT_NUMBER` | GCP Project Number (*Required for authorizationConfig*) | `123456789012` |
| `LOCATION` | Discovery Engine Location | `global` |
| `COLLECTION` | Discovery Engine Collection | `default_collection` |
| `ENGINE_ID` | SharePoint Engine/Datastore Identifier | `sharepoint-search-engine` |
| `AUTH_NAME` | Session State OAuth Token Key | `sharepoint_oauth` |
| `MODEL_NAME` | Gemini Model Identifier | `gemini-2.0-flash` |

---

## 🚀 Quickstart & Testing

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Run Automated Verification Test Suite

Run the included 5-tier test suite to verify OAuth token extraction, 401 expiry detection, timeout handling, and multi-schema parsing:

```bash
python3 test_agent.py
```

Expected Output:
```text
==================================================
   Running Production-Hardened ADK Test Suite
==================================================

--- Test 1: Active User OAuth Token Propagation ---
✅ Test 1 PASSED: OAuth Token & X-Goog-User-Project headers sent successfully.

--- Test 2: HTTP 401 Token Expiry Handling ---
✅ Test 2 PASSED: 401 Unauthorized caught and converted to AUTH_EXPIRED signal.

--- Test 3: HTTP Timeout Exception Handling ---
✅ Test 3 PASSED: Connection timeout caught gracefully without crashing.

--- Test 4: Multi-Schema JSON Result Parsing ---
✅ Test 4 PASSED: Successfully extracted title/link from structData fallback schema.

--- Test 5: Agent Configuration & System Prompt ---
✅ Test 5 PASSED: Agent configuration and prompt rules verified.

🎉 ALL 5 PRODUCTION TESTS PASSED SUCCESSFULLY!
```

---

## 🧬 AlphaEvolve Reranker Optimization

To run the DeepMind AlphaEvolve evaluation benchmark on search result reranking:

```bash
python3 ae_experiment/evaluator.py --program-dir ae_experiment --output-file /tmp/eval_output.json
```

Baseline Result:
```json
{
  "score": 0.8998,
  "insights": [
    { "label": "precision", "text": "100.0% (2/2)" },
    { "label": "latency_ms", "text": "0.01ms" },
    { "label": "verification", "text": "2/2 passed" }
  ]
}
```

---

## 📦 Deployment (`agent.yaml`)

Deploy using `google-agents-cli` or Vertex AI Reasoning Engine:

```yaml
name: sharepoint_knowledge_agent
display_name: "SharePoint ACL-Aware Knowledge Agent"
version: "1.0.0"
entrypoint: "agent:root_agent"

env:
  PROJECT_ID: "your-gcp-project-id"
  PROJECT_NUMBER: "123456789012"
  LOCATION: "global"
  ENGINE_ID: "sharepoint-search-engine"

authorizationConfig:
  oauthClient:
    name: "sharepoint_oauth"
    provider: "AZURE_AD"
    scopes:
      - "https://graph.microsoft.com/Files.Read.All"
      - "https://graph.microsoft.com/Sites.Read.All"

  stateInjection:
    - targetKey: "sharepoint_oauth"
      sourceClaim: "access_token"

  resource: "projects/123456789012/locations/global/authorizations/sharepoint-oauth-config"
```

To deploy via `agents-cli`:

```bash
agents-cli deploy --agent-manifest agent.yaml
```

---

## 📜 References & Acknowledgments

- **Veer Muchandi**: [ADK Gemini Enterprise Datastore Connector Specification](https://github.com/VeerMuchandi/rad-skills/blob/main/adk_ge_datastore_connector/SKILL.md)
- **Lukas Geiger**: [Vertex GenAI A2A GE OAuth Reference Architecture](https://github.com/ljogeiger/VertexGenAISamples/tree/main/public/a2a_ge_oauth_example)
- **Google ADK Framework**: [Google Agent Development Kit](https://github.com/google/adk-python)
