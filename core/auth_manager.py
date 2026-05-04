import time
import requests
from eth_account import Account
from web3 import Web3
from py_clob_client_v2 import ClobClient, ApiCreds, SignatureTypeV2, AssetType, BalanceAllowanceParams
from utils.logger import logger_instance

USDC_NATIVE_ADDRESS = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
USDC_BRIDGED_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
CLOB_EXCHANGE_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEG_RISK_ADAPTER_ADDRESS = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
PUSD_ADDRESS = "0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb"

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

ERC1155_ABI = [
    {"constant": True, "inputs": [{"name": "account", "type": "address"}, {"name": "operator", "type": "address"}], "name": "isApprovedForAll", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "operator", "type": "address"}, {"name": "approved", "type": "bool"}], "name": "setApprovalForAll", "outputs": [], "type": "function"}
]

POLYGON_RPC_LIST = [
    "https://polygon-bor-rpc.publicnode.com",
    "https://1rpc.io/matic",
    "https://rpc.ankr.com/polygon",
    "https://polygon-mainnet.public.blastapi.io",
]

class AuthManager:
    def __init__(self, private_key: str, funder_address: str, rpc_url: str = None):
        self.private_key = private_key
        self.eoa_address = Web3.to_checksum_address(Account.from_key(private_key).address)
        self.funder_address = Web3.to_checksum_address(funder_address) if funder_address else self.eoa_address
        self.w3 = self._connect_rpc(rpc_url)
        self.clob_client = self._init_clob()

        self.usdc_native = self.w3.eth.contract(address=Web3.to_checksum_address(USDC_NATIVE_ADDRESS), abi=ERC20_ABI)
        self.usdc_bridged = self.w3.eth.contract(address=Web3.to_checksum_address(USDC_BRIDGED_ADDRESS), abi=ERC20_ABI)
        self.pusd_contract = self.w3.eth.contract(address=Web3.to_checksum_address(PUSD_ADDRESS), abi=ERC20_ABI)
        self.ctf_contract = self.w3.eth.contract(address=Web3.to_checksum_address(CTF_ADDRESS), abi=ERC1155_ABI)
        
        self.active_usdc = self._detect_active_usdc()

    def _detect_active_usdc(self):
        # В V2 приоритет за PolyUSD (pUSD)
        if self.pusd_contract.functions.balanceOf(self.funder_address).call() > 0:
            return self.pusd_contract
        # Fallback на USDC для совместимости
        if self.usdc_native.functions.balanceOf(self.funder_address).call() > 0:
            return self.usdc_native
        return self.usdc_bridged

    def _connect_rpc(self, rpc_url: str = None) -> Web3:
        urls = [rpc_url] if rpc_url else POLYGON_RPC_LIST
        for url in urls:
            try:
                w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 10}))
                block = w3.eth.block_number
                if block > 0:
                    logger_instance.info("AuthManager", f"RPC подключен: {url} (блок #{block})")
                    return w3
            except Exception as e:
                logger_instance.warning("AuthManager", f"RPC недоступен {url}: {str(e)[:80]}")
        raise ConnectionError("Не удалось подключиться ни к одному Polygon RPC")

    def _init_clob(self) -> ClobClient:
        last_err = None
        
        # Если funder_address отличается от EOA, значит мы используем Deposit Wallet (Proxy/Safe)
        sig_type = SignatureTypeV2.POLY_GNOSIS_SAFE if self.funder_address != self.eoa_address else SignatureTypeV2.EOA

        for attempt in range(3):
            try:
                temp_client = ClobClient(
                    host="https://clob.polymarket.com",
                    chain_id=137,
                    key=self.private_key,
                    signature_type=sig_type,
                    funder=self.funder_address
                )
                creds = temp_client.create_or_derive_api_key()
                client = ClobClient(
                    host="https://clob.polymarket.com",
                    chain_id=137,
                    key=self.private_key,
                    creds=creds,
                    signature_type=sig_type,
                    funder=self.funder_address
                )
                logger_instance.info("AuthManager", f"CLOB API подключен (Signature: {sig_type.name})")
                return client
            except Exception as e:
                last_err = e
                logger_instance.warning("AuthManager", f"CLOB попытка {attempt+1}/3: {str(e)[:80]}")
                time.sleep(2)
        raise ConnectionError(f"Не удалось подключиться к CLOB API: {last_err}")

    def get_gas_price(self) -> int:
        try:
            resp = requests.get("https://gasstation.polygon.technology/v2", timeout=5).json()
            fast_max_fee = resp["fast"]["maxFee"]
            return self.w3.to_wei(fast_max_fee, 'gwei')
        except Exception as e:
            logger_instance.warning("AuthManager", f"Polygon Gas Station failed: {str(e)}, using fallback")
            return self.w3.eth.gas_price

    def get_matic_balance(self) -> float:
        balance_wei = self.w3.eth.get_balance(self.funder_address)
        return float(self.w3.from_wei(balance_wei, 'ether'))

    def get_usdc_balance(self) -> float:
        balance_mwei = self.active_usdc.functions.balanceOf(self.funder_address).call()
        return balance_mwei / 1_000_000.0

    def _send_tx(self, tx_build):
        signed_tx = self.w3.eth.account.sign_transaction(tx_build, private_key=self.private_key)
        raw = signed_tx.raw_transaction if hasattr(signed_tx, "raw_transaction") else signed_tx.rawTransaction
        tx_hash = self.w3.eth.send_raw_transaction(raw)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        return receipt

    def ensure_triple_approve(self, order_usdc: float):
        if self.funder_address != self.eoa_address:
            logger_instance.info("AuthManager", "Используется Deposit Wallet, пропускаем on-chain апрувы (управляются UI)")
            self._sync_backend_balances()
            return

        matic_bal = self.get_matic_balance()
        logger_instance.info("AuthManager", f"Matic balance: {matic_bal}")

        clob_exchange_addr = Web3.to_checksum_address(CLOB_EXCHANGE_ADDRESS)
        neg_risk_addr = Web3.to_checksum_address(NEG_RISK_ADAPTER_ADDRESS)
        order_mwei = int(order_usdc * 1_000_000)

        usdc_allowance = self.active_usdc.functions.allowance(self.funder_address, clob_exchange_addr).call()
        if usdc_allowance < order_mwei:
            logger_instance.info("AuthManager", "Approving USDC for CLOB")
            tx = self.active_usdc.functions.approve(clob_exchange_addr, 2**256 - 1).build_transaction({
                'from': self.funder_address,
                'nonce': self.w3.eth.get_transaction_count(self.funder_address),
                'gasPrice': self.get_gas_price()
            })
            self._send_tx(tx)

        ctf_approved = self.ctf_contract.functions.isApprovedForAll(self.funder_address, clob_exchange_addr).call()
        if not ctf_approved:
            logger_instance.info("AuthManager", "Approving CTF for CLOB")
            tx = self.ctf_contract.functions.setApprovalForAll(clob_exchange_addr, True).build_transaction({
                'from': self.funder_address,
                'nonce': self.w3.eth.get_transaction_count(self.funder_address),
                'gasPrice': self.get_gas_price()
            })
            self._send_tx(tx)

        neg_risk_approved = self.ctf_contract.functions.isApprovedForAll(self.funder_address, neg_risk_addr).call()
        if not neg_risk_approved:
            logger_instance.info("AuthManager", "Approving CTF for Neg Risk Adapter")
            tx = self.ctf_contract.functions.setApprovalForAll(neg_risk_addr, True).build_transaction({
                'from': self.funder_address,
                'nonce': self.w3.eth.get_transaction_count(self.funder_address),
                'gasPrice': self.get_gas_price()
            })
            self._send_tx(tx)
        
        logger_instance.info("AuthManager", "Triple approve verified")
        self._sync_backend_balances()

    def _sync_backend_balances(self):
        sig_type = SignatureTypeV2.POLY_GNOSIS_SAFE if self.funder_address != self.eoa_address else SignatureTypeV2.EOA
        try:
            self.clob_client.update_balance_allowance(
                BalanceAllowanceParams(
                    asset_type=AssetType.COLLATERAL,
                    signature_type=sig_type
                )
            )
            logger_instance.info("AuthManager", "Баланс COLLATERAL синхронизирован с Polymarket")
        except Exception as e:
            logger_instance.warning("AuthManager", f"Ошибка при синхронизации баланса с Polymarket: {e}")
