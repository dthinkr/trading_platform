import asyncio
from typing import Dict, List, Tuple, Optional
from core.data_models import TransactionModel

class TransactionManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.transaction_list: List[TransactionModel] = []
        self.transaction_queue: asyncio.Queue = asyncio.Queue()
        self._last_transaction_price: Optional[float] = None

    async def create_transaction(self, bid: Dict, ask: Dict, transaction_price: float) -> Tuple[str, str, TransactionModel]:
        bid_id, ask_id = bid["id"], ask["id"]

        transaction = TransactionModel(
            trading_session_id=self.session_id,
            bid_order_id=bid_id,
            ask_order_id=ask_id,
            price=transaction_price,
            informed_trader_progress=bid.get("informed_trader_progress") or ask.get("informed_trader_progress")
        )

        self.transaction_list.append(transaction)
        await self.transaction_queue.put(transaction)
        self._last_transaction_price = transaction_price

        return ask["trader_id"], bid["trader_id"], transaction

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