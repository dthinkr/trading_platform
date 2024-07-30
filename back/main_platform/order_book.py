from sortedcontainers import SortedDict
from structures import OrderStatus, OrderType
from typing import Dict, List, Tuple, Optional

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
        if order_id in self.all_orders:
            order = self.all_orders[order_id]
            price = order["price"]
            order_type = order["order_type"]

            if order_type == OrderType.BID:
                self.bids[price].remove(order)
                if not self.bids[price]:
                    del self.bids[price]
            else:
                self.asks[price].remove(order)
                if not self.asks[price]:
                    del self.asks[price]

            del self.all_orders[order_id]
            return True
        return False

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
        
        while self.asks and self.bids:
            best_ask = self.asks.peekitem(0)
            best_bid = self.bids.peekitem(-1)

            if best_ask[0] > best_bid[0]:
                break  # No more matches possible

            ask = self.asks[best_ask[0]].pop(0)
            bid = self.bids[best_bid[0]].pop()

            if not self.asks[best_ask[0]]:
                del self.asks[best_ask[0]]
            if not self.bids[best_bid[0]]:
                del self.bids[best_bid[0]]

            transaction_price = (best_ask[0] + best_bid[0]) / 2
            matched_orders.append((ask, bid, transaction_price))

            # Remove matched orders from self.all_orders
            del self.all_orders[ask["id"]]
            del self.all_orders[bid["id"]]

        return matched_orders