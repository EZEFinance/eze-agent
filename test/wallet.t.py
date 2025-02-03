import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from wallet import AgentWallet

agent = AgentWallet()
agent.create_wallet("0x0000000000000000000000000000000000000001")
agent.fetch_data("0x0000000000000000000000000000000000000001")