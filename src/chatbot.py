import os
import sys
import time

from dotenv import load_dotenv
import json
import os
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
from langchain.tools import Tool

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper

wallet_data_file = "wallet_data.txt"

load_dotenv()

JSON_FILE = "knowledge.json"

def load_knowledge_base():
    """Load JSON data and create a retriever using FAISS."""
    with open(JSON_FILE, "r") as f:
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
    retriever = vectorstore.as_retriever()
    return retriever

def initialize_agent():
    """Initialize the agent with CDP Agentkit and JSON Knowledge Base."""
    llm = ChatOpenAI(model="gpt-4o")
    retriever = load_knowledge_base()
    
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
    
    config = {"configurable": {"thread_id": "CDP Agent with JSON Knowledge Base"}}

    return create_react_agent(llm, tools=tools), config

def run_chat_mode(agent_executor, config):
    """Run the agent interactively based on user input."""
    print("Starting chat mode... Type 'exit' to end.")
    while True:
        try:
            user_input = input("\nPrompt: ")
            if user_input.lower() == "exit":
                break

            response = agent_executor.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )

            print("Data Output Agent:")
            print(response["messages"][-1].content)

        except KeyboardInterrupt:
            print("Goodbye Agent!")
            sys.exit(0)


def main():
    """Start the chatbot agent."""
    agent_executor, config = initialize_agent()
    run_chat_mode(agent_executor=agent_executor, config=config)


if __name__ == "__main__":
    print("Starting Agent...")
    main()
    
    
# Kurang cek store wallet_data.txt
# Cek interaksi dengan private key
