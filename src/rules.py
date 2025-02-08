from checker import *

import os
import orjson
from cdp import Cdp, Wallet, WalletData
from utils import get_env_variable

class AgentWalletSync:
    def __init__(self):
        self.api_key = get_env_variable("CDP_API_KEY_NAME")
        self.private_key = get_env_variable("CDP_API_KEY_PRIVATE_KEY")
        self.file_path = "./data/wallet.json"
        Cdp.configure(self.api_key, self.private_key)

    def fetch_data(self, user_address):
        existing_data = self._load_existing_data()

        for entry in existing_data:
            if entry["user_address"] == user_address:
                wallet_data_dict = entry["data"]
                wallet_data = WalletData.from_dict(wallet_data_dict)
                wallet = Wallet.import_wallet(wallet_data)
                
                return wallet

        print(f"No wallet data found for user address: {user_address}")
        return None
    
    def _get_token_ca(self, asset_id):
        match asset_id:
            case "usdc":
                return "0x8fD29CC673C16d0466D5eA0250dC3d040554F4a3"
            case "uni":
                return "0xbb072b81D265D4F574b324Cea7469C9369281Da0"
            case "weth":
                return "0x1133c55280Be106f985622bF56dcc7Fb3C3D6Ee0"
            case "usdt":
                return "0xaa7DcAae6C6e579A326B860572Da90A149Dc1266"
            case "dai":
                return "0x9A410E847e6161c96C72a7C40beaDAD5c86ea6aE"
    
    def swap(self, user_address, spender, token_in, token_out, amount):
        approve_abi = self._read_abi("./abi/MockToken.json")
        amount = int(amount) * (10 ** 6)
        
        wallet = self.fetch_data(user_address)
        approve_incovation = wallet.invoke_contract(
            contract_address=token_in,
            abi=approve_abi,
            method="approve",
            args={"spender": spender, "amount": str(int(amount + 10))}
        )
        approve_incovation.wait()
        
        abi = self._read_abi("./abi/EZEFinance.json")
        
        invocation = wallet.invoke_contract(
            contract_address="0xc34aE34Da7051ac971638d3F09FDF516Ea48C5c9",
            abi=abi,
            method="swap",
            args={"tokenIn": token_in, "tokenOut": token_out, "amountIn": str(int(amount))}
        )

        invocation.wait()
        
        return invocation.transaction_hash
    
    def stake(self, user_address, asset_id, spender, amount):
        approve_abi = self._read_abi("./abi/MockToken.json")
        amount = int(amount) * (10 ** 6)
        
        wallet = self.fetch_data(user_address)
        approve_incovation = wallet.invoke_contract(
            contract_address=asset_id,
            abi=approve_abi,
            method="approve",
            args={"spender": spender, "amount": str(int(amount + 10))}
        )
        approve_incovation.wait()
        
        abi = self._read_abi("./abi/MockStake.json")
        
        invocation = wallet.invoke_contract(
            contract_address=spender,
            abi=abi,
            method="stake",
            args={"_days": str(0), "_amount": str(int(amount))}
        )

        invocation.wait()
        
        return invocation.transaction_hash
    
    
    def unstake(self, user_address, protocol):        
        abi = self._read_abi("./abi/MockStake.json")
        wallet = self.fetch_data(user_address)
        invocation = wallet.invoke_contract(
            contract_address=protocol,
            abi=abi,
            method="withdrawAll"
        )

        invocation.wait()
        
        return invocation.transaction_hash


    def _read_abi(self, abi_path):
        with open(abi_path, 'r') as file:
            return orjson.loads(file.read())


    def _load_existing_data(self):
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, 'rb') as file:
            return orjson.loads(file.read())

    def _save_data(self, data):
        with open(self.file_path, 'wb') as file:
            file.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))


def handle_user(user_address: str):
    user_risk = get_risk(user_address)
    user_staked = get_data_staked(user_address)
    
    match user_risk:
        case "low":
            handle_low_risk(user_address, user_staked)
        case "medium":
            handle_high_risk(user_address, user_staked)
        case "high":
            handle_high_risk(user_address, user_staked)


def handle_low_risk(user_address, user_staked):
    for i in range(len(user_staked)):
        protocol, response_raw = get_apy(filter='highest')
        result = handle_protocols(user_staked[i], protocol, response_raw)
        
        if result is None:
            continue

        from_protocol, token_ca, amount = result
        try:
            agent = AgentWalletSync()
            agent.unstake(user_address, from_protocol)
            agent.swap(user_address, spender="0xc34aE34Da7051ac971638d3F09FDF516Ea48C5c9", token_in=token_ca, token_out=protocol[2], amount=amount)
            agent.stake(user_address, protocol[2], protocol[0], amount)
            print("success")
        except Exception as e:
            print(e)
    

def handle_high_risk(user_address, user_staked):
    for i in range(len(user_staked)):
        protocol, response_raw = get_apy(filter='highest-best')
        result = handle_protocols(user_staked[i], protocol, response_raw)
        
        if result is None:
            continue

        from_protocol, token_ca, amount = result
        
        try:
            agent = AgentWalletSync()
            agent.unstake(user_address, from_protocol)
            agent.swap(user_address, spender="0xc34aE34Da7051ac971638d3F09FDF516Ea48C5c9", token_in=token_ca, token_out=protocol[2], amount=amount)
            agent.stake(user_address, protocol[2], protocol[0], amount)
            print("success")
        except Exception as e:
            print(e)


def get_apy(filter):
    result = requests.get('https://eze-api.vercel.app/staking')
    response = result.json()
    
    if filter == 'highest':
        protocol = [(item['addressStaking'], float(item['apy']), item['addressToken']) for item in response if item['stablecoin'] is True]
        highest_apy = max(protocol, key=lambda x: x[1])

        return highest_apy, response
    
    elif filter == 'highest-best':
        protocol = [(item['addressStaking'], float(item['apy']), item['addressToken']) for item in response]
        highest_apy = max(protocol, key=lambda x: x[1])

        return highest_apy, response
    

def handle_protocols(user_staked, protocol, response):
    for item in [user_staked]:
        protocol_address = item['protocol']
        if protocol_address != protocol[0]:
            token_ca = [item['addressToken'] for item in response if item['addressStaking'] == protocol_address][0]
            return item['protocol'], token_ca, item['amount']
    return None


def runner():
    with open('./data/wallet.json', 'rb') as file:
        existing_data =  orjson.loads(file.read())
        
    address_list = [item['user_address'] for item in existing_data]
    for address in address_list:
        handle_user(address)


