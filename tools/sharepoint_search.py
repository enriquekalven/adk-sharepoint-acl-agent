import os
import logging
import requests

try:
    from google.adk.tools import ToolContext, tool
except ImportError:
    from google.adk.tools import ToolContext
    def tool(func=None, **kwargs):
        return func if func else lambda f: f

from google.auth import default
from google.auth.transport import requests as auth_requests

# Production Logging Configuration
logger = logging.getLogger(__name__)

@tool
def query_sharepoint(query: str, tool_context: ToolContext) -> str:
    """Queries the secure SharePoint Discovery Engine datastore using the user's active session credentials.
    
    Enforces native SharePoint Access Control Lists (ACLs) via session-injected OAuth tokens.
    
    Args:
        query: The search query to run against the SharePoint datastore.
        tool_context: ADK ToolContext containing injected session state.
    """
    # 1. Fetch Auth Name from Environment
    auth_name = os.getenv("AUTH_NAME", "sharepoint_oauth")
    access_token = None
    
    if tool_context and tool_context.state:
        access_token = tool_context.state.get(auth_name)
        
    # 2. Hybrid Fallback (Prod: Session User Token | Dev: Local ADC)
    if access_token:
        logger.info("[Security] Propagating session-injected User OAuth Token (ACLs active).")
    else:
        logger.warning("[Development] User token missing in ToolContext. Falling back to local Application Default Credentials (ADC).")
        try:
            creds, _ = default()
            auth_req = auth_requests.Request()
            creds.refresh(auth_req)
            access_token = creds.token
        except Exception as err:
            logger.error(f"Failed to refresh local ADC: {err}")
            return "Authentication Error: Unable to acquire active credentials for search."

    # 3. Target Configuration & Environment Resolution
    project_id = os.getenv("PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "default-project"))
    location = os.getenv("LOCATION", "global")
    collection = os.getenv("COLLECTION", "default_collection")
    engine_id = os.getenv("ENGINE_ID", "sharepoint-search-engine")
    
    url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/{collection}/engines/{engine_id}/servingConfigs/default_search:search"
    
    # Header hardening: Add X-Goog-User-Project for GCP API Gateway attribution
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id
    }
    
    # Payload hardening: Add spell correction and explicit search specs
    payload = {
        "query": query,
        "pageSize": 3,
        "spellCorrectionSpec": {"mode": "AUTO"},
        "contentSearchSpec": {
            "snippetSpec": {"maxSnippetCount": 1, "returnSnippet": True},
            "summarySpec": {"summaryResultCount": 3}
        }
    }
    
    try:
        # Timeouts: 3.05s connect timeout, 10.0s read timeout
        response = requests.post(url, json=payload, headers=headers, timeout=(3.05, 10.0))
        
        # Blindspot 1 Fix: Handle Token Expiry (401 Unauthorized)
        if response.status_code == 401:
            logger.error("Discovery Engine returned 401 Unauthorized. User OAuth token expired or invalid.")
            return "AUTH_EXPIRED: Your SharePoint session authorization token has expired. Please re-authenticate."
            
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        if not results:
            return "No matching documents found in SharePoint repository for your permission level."
            
        # Blindspot 4 Fix: Robust Multi-Schema Field Extraction
        formatted_excerpts = []
        for i, res in enumerate(results, 1):
            doc = res.get("document", {})
            derived = doc.get("derivedStructData", {})
            struct = doc.get("structData", {})
            
            # Safe title extraction
            title = derived.get("title") or struct.get("title") or doc.get("name", f"Document #{i}")
            link = derived.get("link") or struct.get("link") or "#"
            
            # Safe snippet extraction
            snippets = derived.get("snippets", [])
            snippet_text = "No preview available."
            if isinstance(snippets, list) and len(snippets) > 0 and isinstance(snippets[0], dict):
                snippet_text = snippets[0].get("snippet", snippet_text)
                
            formatted_excerpts.append(
                f"[{i}] Title: {title}\nLink: {link}\nExcerpt: {snippet_text}\n"
            )
            
        return "\n".join(formatted_excerpts)
        
    except requests.exceptions.Timeout:
        logger.error("SharePoint Discovery Engine REST query timed out.")
        return "Search Error: Request timed out while searching SharePoint. Please refine your query."
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error during SharePoint search: {http_err}", exc_info=True)
        return "Search Error: Unable to complete query due to a downstream API error."
    except Exception as e:
        logger.error(f"Unexpected error querying SharePoint Datastore: {e}", exc_info=True)
        return "Search Error: An internal error occurred while querying enterprise knowledge."
