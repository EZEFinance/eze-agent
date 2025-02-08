import orjson
import requests
from web3 import Web3
from cdp import Cdp, Wallet, WalletData
from utils import get_env_variable

api_key = get_env_variable("CDP_API_KEY_NAME")
private_key = get_env_variable("CDP_API_KEY_PRIVATE_KEY")

Cdp.configure(api_key, private_key)

def _load_existing_data():
    with open('data/wallet.json', 'rb') as file:
        return orjson.loads(file.read())
    
def fetch_data(user_address):
    existing_data = _load_existing_data()

    for entry in existing_data:
        if entry["user_address"] == user_address:
            wallet_data_dict = entry["data"]
            wallet_data = WalletData.from_dict(wallet_data_dict)
            wallet = Wallet.import_wallet(wallet_data)
            
            return wallet        

def get_data_staked(user_address):
    wallet = fetch_data(user_address)
    address = wallet.default_address.address_id
    
    rpc_url = "https://api.developer.coinbase.com/rpc/v1/base-sepolia/vIyOU1PrjnUku5b1y2FGu416eItcu3KH"
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    result = requests.get("https://eze-api.vercel.app/staking")
    response = result.json()
    address_protocol = [item['addressStaking'] for item in response]


    with open("abi/MockStake.json", 'r') as file:
        contract_abi = orjson.loads(file.read())
    
    result_amount = []
    for i in range(len(address_protocol)):
        contract_address = address_protocol[i]
        contract = w3.eth.contract(address=contract_address, abi=contract_abi)
        try:
            w3.to_checksum_address(address)
            balance = contract.functions.getAmountStakeByUser(address).call()
            readable_balance = balance / (10 ** 6)
            if int(readable_balance) > 0:
                user_staked = {
                    "protocol": contract_address,
                    "amount": readable_balance, 
                }
                result_amount.append(user_staked)
                
        except Exception as e:
            print(f"Error retrieving balance: {e}")
    
    return result_amount

def get_risk(user_address):
    wallet_data = _load_existing_data()
    for entry in wallet_data:
        if entry["user_address"] == user_address:
            return entry["risk_profile"]
            
            
if __name__ == "__main__":
    user_wallet = "0x0000000000000000000000000000000000000003"
    user_risk = get_risk(user_wallet)
    result = get_data_staked(user_wallet)
    print(result)