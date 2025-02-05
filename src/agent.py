import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from typing import Optional

import pandas as pd
from fastapi import HTTPException
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper

class CdpAgent:
    def __init__(self, knowledge_file: str, max_workers: int = 3):
        self.knowledge_file = knowledge_file
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.agent_executor = None
    
    async def initialize(self):
        """Initialize the agent with required components."""
        try:
            retriever = await self.load_knowledge_base()
            loop = asyncio.get_event_loop()
            
            self.agent_executor = await loop.run_in_executor(
                self.thread_pool,
                self._sync_initialize_agent,
                retriever
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize agent: {str(e)}")
    
    async def load_knowledge_base(self):
        """Load and prepare the knowledge base."""
        try:
            loop = asyncio.get_event_loop()
            async with asyncio.Lock():
                return await loop.run_in_executor(self.thread_pool, self._sync_load_knowledge_base)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load knowledge base: {str(e)}")
    
    def _sync_load_knowledge_base(self):
        """Synchronous knowledge base loading."""
        with open(self.knowledge_file, "r") as f:
            data = json.load(f)
            
        df = pd.DataFrame(data)
        docs = [
            Document(
                page_content=f"Project: {row['project']}, Chain: {row['chain']}, Symbol: {row['symbol']}, TVL: {row['tvlUsd']}, APY: {row['apyBase']}, Stablecoin: {row['stablecoin']}",
                metadata={"symbol": row["symbol"], "project": row["project"]}
            )
            for _, row in df.iterrows()
        ]

        vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
        return vectorstore.as_retriever()
    
    def _sync_initialize_agent(self, retriever):
        """Synchronous agent initialization."""
        llm = ChatOpenAI(model="gpt-4o-mini-2024-07-18")
        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
        qa_tool = Tool(
            name="KnowledgeBaseQA",
            func=lambda query: qa_chain.run(query),
            description="Use this to search for TVL, APY, or DeFi information based on JSON knowledge base.",
        )

        agentkit = CdpAgentkitWrapper()
        cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)

        tools = cdp_toolkit.get_tools()
        tools.append(qa_tool)
        
        return create_react_agent(llm, tools=tools)

    async def process_query(self, query: str, thread_id: Optional[str] = None):
        """Process a query using the agent."""
        if not self.agent_executor:
            raise HTTPException(status_code=500, detail="Agent not initialized")
            
        try:
            config = {"configurable": {"thread_id": thread_id or "CDP Agent API"}}
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                self.thread_pool,
                lambda: self.agent_executor.invoke(
                    {"messages": [HumanMessage(content=query)]},
                    config=config
                )
            )
            
            return response["messages"][-1].content
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")