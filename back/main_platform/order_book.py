from sortedcontainers import SortedDict
from structures import OrderStatus, OrderType
from typing import Dict, List, Tuple, Optional
from uuid import UUID

class OrderBook:
    def __init__(self):
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.all_orders = {}

    def __getitem__(self, key):
        if key == 'bids':
            return [{"x": k, "y": sum(order['amount'] for order in v)} for k, v in reversed(self.bids.items())]
        elif key == 'asks':
            return [{"x": k, "y": sum(order['amount'] for order in v)} for k, v in self.asks.items()]
        else:
            return self.all_orders[key]

    def __setitem__(self, key, value):
        self.all_orders[key] = value

    def place_order(self, order_dict: Dict) -> Dict:
        order_id = order_dict["id"]
        order_dict["status"] = OrderStatus.ACTIVE.value
        self.all_orders[order_id] = order_dict

        price = order_dict["price"]
        if order_dict["order_type"] == OrderType.BID.value:
            if price not in self.bids:
                self.bids[price] = []
            self.bids[price].append(order_dict)
        else:
            if price not in self.asks:
                self.asks[price] = []
            self.asks[price].append(order_dict)

        return order_dict

    def get_order_book_snapshot(self) -> Dict:
        return {
            "bids": self['bids'],
            "asks": self['asks'],
        }

    def clear(self):
        self.bids.clear()
        self.asks.clear()
        self.all_orders.clear()

    def cancel_order(self, order_id: str) -> bool:
        try:
            uuid_order_id = UUID(order_id)
        except ValueError:
            return False

        if uuid_order_id not in self.all_orders:
            return False
        
        order = self.all_orders[uuid_order_id]
        price = order["price"]
        order_type = order["order_type"]

        if order_type == OrderType.BID.value:
            if price in self.bids and order in self.bids[price]:
                self.bids[price].remove(order)
                if not self.bids[price]:
                    del self.bids[price]
            else:
                return False
        elif order_type == OrderType.ASK.value:
            if price in self.asks and order in self.asks[price]:
                self.asks[price].remove(order)
                if not self.asks[price]:
                    del self.asks[price]
            else:
                return False
        else:
            return False

        del self.all_orders[uuid_order_id]
        return True    
            
    def get_spread(self) -> Tuple[Optional[float], Optional[float]]:
        if self.asks and self.bids:
            lowest_ask = self.asks.peekitem(0)[0]
            highest_bid = self.bids.peekitem(-1)[0]
            spread = lowest_ask - highest_bid
            mid_price = (lowest_ask + highest_bid) / 2
            return spread, mid_price
        return None, None

    @property
    def active_orders(self) -> Dict:
        return {k: v for k, v in self.all_orders.items() if v["status"] == OrderStatus.ACTIVE.value}

    def clear_orders(self) -> List[Tuple[Dict, Dict, float]]:
        matched_orders = []
        while self.bids and self.asks:
            best_bid = max(self.bids.keys())
            best_ask = min(self.asks.keys())
            if best_bid >= best_ask:
                bid = self.bids[best_bid][0]
                ask = self.asks[best_ask][0]
                transaction_price = (best_bid + best_ask) / 2
                matched_orders.append((ask, bid, transaction_price))
                
                # Remove the matched orders from the price levels
                self.bids[best_bid].pop(0)
                self.asks[best_ask].pop(0)
                
                # Remove empty price levels
                if not self.bids[best_bid]:
                    del self.bids[best_bid]
                if not self.asks[best_ask]:
                    del self.asks[best_ask]
            else:
                break
        
        # Remove matched orders from self.all_orders after creating transactions
        for ask, bid, _ in matched_orders:
            if ask['id'] in self.all_orders:
                del self.all_orders[ask['id']]
            if bid['id'] in self.all_orders:
                del self.all_orders[bid['id']]
        
        return matched_orders