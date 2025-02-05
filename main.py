import ast
import time
import json

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.agent import CdpAgent
from models.schemas import QueryRequest, QueryResponse
load_dotenv()

app = FastAPI(
    title="CDP Agent API",
    description="API for interacting with CDP Agent with Knowledge Base",
    version="1.0.0"
)

JSON_FILE = "models/knowledge.json"

cdp_agent = CdpAgent(knowledge_file=JSON_FILE)

@app.on_event("startup")
async def startup_event():
    """Initialize agent when the API starts."""
    await cdp_agent.initialize()

@app.post("/query")
async def query_agent_sync(request: QueryRequest):
    """
    Synchronous endpoint to query the CDP agent
    """
    try:
        start_time = time.time()
        
        response = await cdp_agent.process_query(
            query=request.query,
            thread_id=request.thread_id
        )

        parsed_response = json.loads(response) if isinstance(response, str) else response
        formatted_response = {
            "chain": str(parsed_response.get("chain", "")),
            "project": str(parsed_response.get("project", "")),
            "symbol": str(parsed_response.get("symbol", "")),
            "tvlUsd": int(parsed_response.get("tvlUsd", 0)),
            "apyBase": float(parsed_response.get("apyBase", 0.0)),
            "stablecoin": parsed_response.get("stablecoin", "false").lower() == "true"
        }
        processing_time = time.time() - start_time

        response_json = {
            "response": [formatted_response],
            "thread_id": request.thread_id or "CDP Agent API",
            "processing_time": processing_time
        }

        return JSONResponse(content=response_json)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "thread_pool_info": {
            "max_workers": cdp_agent.thread_pool._max_workers,
            "active_threads": cdp_agent.thread_pool._work_queue.qsize()
        }
    }
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)