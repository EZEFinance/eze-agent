import os
import orjson
from cdp import Cdp, Wallet, WalletData
from utils import get_env_variable

class AgentWallet:
    def __init__(self):
        self.api_key = get_env_variable("CDP_API_KEY_NAME")
        self.private_key = get_env_variable("CDP_API_KEY_PRIVATE_KEY")
        self.file_path = "./data/wallet.json"

    def create_wallet(self, user_address):
        existing_data = self._load_existing_data()
        
        for entry in existing_data:
            if entry["user_address"] == user_address:
                print(f"Wallet already exists for user address: {user_address}")
                return
        
        Cdp.configure(self.api_key, self.private_key)
        wallet = Wallet.create(network_id="base-sepolia")
        wallet_data = wallet.export_data()
        self.save_wallet_data(wallet_data, user_address)
        print(wallet_data)

    def save_wallet_data(self, wallet_data, user_address):
        wallet_data_dict = wallet_data.to_dict()
        output_data = {
            "user_address": user_address,
            "data": wallet_data_dict
        }

        existing_data = self._load_existing_data()
        existing_data.append(output_data)
        self._save_data(existing_data)
        print("Wallet data saved successfully.")

    def fetch_data(self, user_address):
        existing_data = self._load_existing_data()

        for entry in existing_data:
            if entry["user_address"] == user_address:
                wallet_data_dict = entry["data"]
                wallet_data = WalletData.from_dict(wallet_data_dict)
                print("Wallet data loaded successfully.")
                print(wallet_data)
                return wallet_data

        print(f"No wallet data found for user address: {user_address}")
        return None

    def _load_existing_data(self):
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, 'rb') as file:
            return orjson.loads(file.read())

    def _save_data(self, data):
        with open(self.file_path, 'wb') as file:
            file.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
