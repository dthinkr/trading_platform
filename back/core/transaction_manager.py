import asyncio
from typing import Dict, List, Tuple, Optional
from core.data_models import TransactionModel, OrderType

class TransactionManager:
    def __init__(self, market_id: str):
        self.market_id = market_id
        self.transaction_list: List[TransactionModel] = []
        self.transaction_queue: asyncio.Queue = asyncio.Queue()
        self._last_transaction_price: Optional[float] = None


    async def create_transaction(self, bid: Dict, ask: Dict, transaction_price: float) -> Tuple[str, str, TransactionModel, Dict]:
        bid_id, ask_id = bid["id"], ask["id"]

        transaction = TransactionModel(
            trading_market_id=self.market_id,
            bid_order_id=bid_id,
            ask_order_id=ask_id,
            price=transaction_price,
            informed_trader_progress=bid.get("informed_trader_progress") or ask.get("informed_trader_progress")
        )

        self.transaction_list.append(transaction)
        await self.transaction_queue.put(transaction)
        self._last_transaction_price = transaction_price

        transaction_details = {
            "type": "transaction_update",
            "transactions": [
                {
                    "id": order["id"],
                    "price": transaction_price,
                    "type": "ask" if order["order_type"] == OrderType.ASK else "bid",
                    "amount": order["amount"],
                    "trader_id": order["trader_id"],
                }
                for order in [ask, bid]
            ],
            "matched_orders": {
                "bid_order_id": str(bid_id),
                "ask_order_id": str(ask_id),
                "transaction_price": transaction_price,
                "transaction_amount": min(bid["amount"], ask["amount"]),
                "bid_trader_id": bid["trader_id"],
                "ask_trader_id": ask["trader_id"],
                "bid_price": bid["price"],
                "ask_price": ask["price"],
                "timestamp": transaction.timestamp.isoformat(),
            },
        }

        return ask["trader_id"], bid["trader_id"], transaction, transaction_details
    
    @property
    def transactions(self) -> List[Dict]:
        return [transaction.to_dict() for transaction in self.transaction_list]

    @property
    def transaction_price(self) -> Optional[float]:
        return self._last_transaction_price

    async def process_transactions(self) -> None:
        while True:
            try:
                transaction = await asyncio.wait_for(self.transaction_queue.get(), timeout=0.1)
                self.transaction_queue.task_done()
                self._last_transaction_price = transaction.price
            except asyncio.TimeoutError:
                pass