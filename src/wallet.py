import os
import orjson
from cdp import Cdp, Wallet, WalletData
from src.utils import get_env_variable

class AgentWallet:
    def __init__(self):
        self.api_key = get_env_variable("CDP_API_KEY_NAME")
        self.private_key = get_env_variable("CDP_API_KEY_PRIVATE_KEY")
        self.file_path = "./data/wallet.json"
        Cdp.configure(self.api_key, self.private_key)

    def create_wallet(self, user_address):
        existing_data = self._load_existing_data()
        
        for entry in existing_data:
            if entry["user_address"] == user_address:
                print(f"Wallet already exists for user address: {user_address}")
                return
        
        wallet = Wallet.create(network_id="base-sepolia")
        wallet_data = wallet.export_data()
        self.save_wallet_data(wallet_data, user_address)
        

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
                wallet = Wallet.import_wallet(wallet_data)
                
                return wallet

        print(f"No wallet data found for user address: {user_address}")
        return None
    
    def _check_address(self, user_address):
        wallet = self.fetch_data(user_address)
        address = wallet.default_address
        print(address.address_id)
        return address.address_id
    
    # Fund wallet via mpc
    def _fund_wallet(self, user_address):
        wallet = self.fetch_data(user_address)
        faucet = wallet.faucet(asset_id='eth')
        faucet.wait()
        return faucet.transaction_hash
    
    def _transfer(self, user_address, amount, asset_id, destination):
        wallet = self.fetch_data(user_address)
        transaction = wallet.transfer(amount, asset_id, destination)
        transaction.wait()
        return transaction.transaction_hash
    
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
    
    def _get_protocol_ca(self, protocol):
        match protocol:
            case "uniswap":
                return "0x13aB00A1Fae23DCC5618690480cfdE86B04Bbaeb"
            case "compound":
                return "0x71417c20c60eD165026336922925C4f25439B3a0"
            case "renzo":
                return "0xdbE2c044D5F350807c437A1b3748191FE9D83250"
            case "cardano":
                return "0x64D28469CAa42C51C57f42aCfD975E8AC4C1b0D2"
            case "aave":
                return "0x55C30Ff712b97B3692fd4f838D13D84DE8Be38B4"
    
    def mint(self, user_address, asset_id, amount):
        amount = int(amount) * (10 ** 6)
        abi = self._read_abi("./abi/MockToken.json")
        
        wallet = self.fetch_data(user_address)
        address = wallet.default_address.address_id
        
        invocation = wallet.invoke_contract(
            contract_address=self._get_token_ca(asset_id),
            abi=abi,
            method="mint",
            args={"to": address, "amount": str(int(amount))}
        )

        invocation.wait()
        
        return invocation.transaction_hash
    
    
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
    
    def stake(self, user_address, asset_id, protocol, spender, amount):
        approve_abi = self._read_abi("./abi/MockToken.json")
        amount = int(amount) * (10 ** 6)
        
        wallet = self.fetch_data(user_address)
        approve_incovation = wallet.invoke_contract(
            contract_address=self._get_token_ca(asset_id),
            abi=approve_abi,
            method="approve",
            args={"spender": spender, "amount": str(int(amount + 10))}
        )
        approve_incovation.wait()
        
        abi = self._read_abi("./abi/MockStake.json")
        
        invocation = wallet.invoke_contract(
            contract_address=self._get_protocol_ca(protocol),
            abi=abi,
            method="stake",
            args={"_days": str(0), "_amount": str(int(amount))}
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
