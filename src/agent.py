import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import aiohttp
import pandas as pd
from fastapi import HTTPException
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from langchain.tools import Tool
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper

class CdpAgent:
    def __init__(self, url: str, max_workers: int = 3):
        self.url = url
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.agent_executor = None
        self._lock = asyncio.Lock()
        self.knowledge_data = []
    
    async def fetch_knowledge(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                if response.status == 200:
                    self.knowledge_data = await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=f"Failed to fetch {self.url}")

    async def initialize(self):
        async with self._lock:
            await self.fetch_knowledge()
            retriever = await self.create_retriever()
            self.agent_executor = await asyncio.get_event_loop().run_in_executor(
                self.thread_pool,
                self._sync_initialize_agent,
                retriever
            )

    async def create_retriever(self):
        df = pd.DataFrame(self.knowledge_data)
        docs = [
            Document(
                page_content=f"IdProject: {row['idProtocol']}, Chain: {row['chain']}, Symbol: {row['nameToken']}, TVL: {row['tvl']}, APY: {row['apy']}, Stablecoin: {row['stablecoin']}",
                metadata={"symbol": row["nameToken"], "protocol": row["idProtocol"]}
            )
            for _, row in df.iterrows()
        ]

        return await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,
            lambda: FAISS.from_documents(docs, OpenAIEmbeddings()).as_retriever()
        )

    def _sync_initialize_agent(self, retriever):
        llm = ChatOpenAI(model="gpt-4o-mini-2024-07-18")
        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
        qa_tool = Tool(
            name="KnowledgeBaseQA",
            func=lambda query: qa_chain.run(query),
            description="Use this to search for TVL, APY, or DeFi information.",
        )

        agentkit = CdpAgentkitWrapper()
        cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)
        
        tools = cdp_toolkit.get_tools()
        tools.append(qa_tool)
        
        return create_react_agent(llm, tools=tools)

    async def process_query(self, query: str, thread_id: Optional[str] = None):
        await self.initialize()
        config = {"configurable": {"thread_id": thread_id or "CDP Agent API"}}
        return await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,
            lambda: self.agent_executor.invoke(
                {"messages": [HumanMessage(content=query)]},
                config=config
            )["messages"][-1].content
        )