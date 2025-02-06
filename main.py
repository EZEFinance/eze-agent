import time
import json

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import asyncio
from src.agent import CdpAgent, CdpAgentClassifier
from src.wallet import AgentWallet
from models.schemas import *
load_dotenv()

app = FastAPI(
    title="CDP Agent API",
    description="API for interacting with CDP Agent with Knowledge Base",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_KNOWLEDGE = "https://eze-api.vercel.app/staking"

cdp_agent_classifier = CdpAgentClassifier()
cdp_agent = CdpAgent(url=URL_KNOWLEDGE)
agent_wallet = AgentWallet()

@app.on_event("startup")
async def startup_event():
    """Initialize agent when the API starts."""
    await cdp_agent_classifier.initialize()
    await cdp_agent.initialize()


@app.post("/generate-risk-profile")
async def assess_risk(data: str = Body(..., embed=True)):
    """
    Endpoint to assess risk profile based on user responses.
    Returns a JSON with risk assessment level.
    """
    try:
        response = await cdp_agent_classifier.process_query(query=data)
        parsed_response = json.loads(response)
        
        return JSONResponse(content=parsed_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query_agent_sync(request: QueryRequest):
    """
    Synchronous endpoint to query the CDP agent
    """
    try:
        start_time = time.time()
        
        response = await asyncio.wait_for(
            cdp_agent.process_query(query=request.query, thread_id=request.thread_id
            ), timeout=30.0)

        parsed_response = json.loads(response) if isinstance(response, str) else response
        formatted_response = {
            "id_project": str(parsed_response.get("id_project", ""))
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
        
@app.post("/action/create-wallet")
async def create_wallet(request: QueryUserWallet):
    await agent_wallet.create_wallet(
            user_address=request.user_address
        )
    response = {"address": await agent_wallet._check_address(request.user_address)}
    
    return JSONResponse(content=response)
    
    
@app.post("/action/get-wallet")
async def get_wallet(request: QueryUserWallet):
    response = {"address": await agent_wallet._check_address(request.user_address)}
    return JSONResponse(content=response)


@app.post("/action/get-eth-faucet")
async def get_eth_faucet(request: QueryUserWallet):
    response = {"txhash": await agent_wallet._fund_wallet(request.user_address)}
    return JSONResponse(content=response)


@app.post("/action/mint")
async def mint(request: QueryMint):
    response = {"txhash": await agent_wallet.mint(request.user_address, request.asset_id, request.amount)}
    return JSONResponse(content=response)


@app.post("/action/swap")
async def swap(request: QuerySwap):
    response = {"txhash": await agent_wallet.swap(request.user_address, request.spender, request.token_in, request.token_out, request.amount)}
    return JSONResponse(content=response)


@app.post("/action/stake")
async def stake(request: QueryStake):
    response = {"txhash": await agent_wallet.stake(request.user_address, request.asset_id, request.protocol, request.spender, request.amount)}
    return JSONResponse(content=response)

@app.post("/action/unstake")
async def stake(request: QueryUnstake):
    response = {"txhash": await agent_wallet.unstake(request.user_address, request.protocol)}
    return JSONResponse(content=response)


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