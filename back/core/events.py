"""
Event system for trading platform - replaces handle_X pattern with event-driven architecture.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import asyncio
import uuid


# Base event classes
class TradingEvent(ABC):
    """Base class for all trading events."""
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now()


@dataclass
class OrderPlacedEvent(TradingEvent):
    """Event emitted when an order is placed."""
    order_data: Dict[str, Any]
    trader_id: str
    informed_progress: Optional[str] = None
    
    def __post_init__(self):
        super().__init__()


@dataclass
class OrderCancelledEvent(TradingEvent):
    """Event emitted when an order is cancelled."""
    order_id: str
    trader_id: str
    
    def __post_init__(self):
        super().__init__()


@dataclass
class TraderRegisteredEvent(TradingEvent):
    """Event emitted when a trader registers."""
    trader_id: str
    trader_type: str
    gmail_username: Optional[str]
    trader_instance: Any
    
    def __post_init__(self):
        super().__init__()


@dataclass
class InventoryReportEvent(TradingEvent):
    """Event emitted when a trader reports inventory."""
    trader_id: str
    shares: int
    cash: float
    
    def __post_init__(self):
        super().__init__()


@dataclass
class TransactionCreatedEvent(TradingEvent):
    """Event emitted when a transaction is created."""
    transaction: Any
    transaction_details: Dict[str, Any]
    
    def __post_init__(self):
        super().__init__()


@dataclass
class OrderBookUpdatedEvent(TradingEvent):
    """Event emitted when the order book is updated."""
    update_type: str
    details: Dict[str, Any]
    
    def __post_init__(self):
        super().__init__()


@dataclass
class TradingStartedEvent(TradingEvent):
    """Event emitted when trading starts."""
    market_id: str
    
    def __post_init__(self):
        super().__init__()


@dataclass
class TradingStoppedEvent(TradingEvent):
    """Event emitted when trading stops."""
    market_id: str
    
    def __post_init__(self):
        super().__init__()


# Event handler interface
class EventHandler(ABC):
    """Base class for event handlers."""
    
    @abstractmethod
    async def handle(self, event: TradingEvent) -> Optional[Dict[str, Any]]:
        """Handle an event and optionally return a response."""
        pass


# Message bus for event distribution
class MessageBus:
    """Central message bus for event distribution."""
    
    def __init__(self):
        self.handlers: Dict[type, List[EventHandler]] = {}
        self.middleware: List[Callable] = []
    
    def subscribe(self, event_type: type, handler: EventHandler):
        """Subscribe a handler to an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def add_middleware(self, middleware: Callable):
        """Add middleware for cross-cutting concerns."""
        self.middleware.append(middleware)
    
    async def publish(self, event: TradingEvent) -> List[Dict[str, Any]]:
        """Publish an event to all subscribers."""
        responses = []
        
        # Apply middleware
        for middleware in self.middleware:
            event = await middleware(event)
        
        # Get handlers for this event type
        handlers = self.handlers.get(type(event), [])
        
        # Execute all handlers
        for handler in handlers:
            try:
                response = await handler.handle(event)
                if response:
                    responses.append(response)
            except Exception as e:
                # Log error but don't stop other handlers
                print(f"Error in event handler: {e}")
        
        return responses


# Message router for external interfaces
class MessageRouter:
    """Routes external messages to events."""
    
    def __init__(self, message_bus: MessageBus):
        self.bus = message_bus
    
    async def route_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Route an external message to appropriate event."""
        action_type = message.get("type", message.get("action"))
        
        try:
            if action_type == "add_order":
                event = OrderPlacedEvent(
                    order_data=message,
                    trader_id=message.get("trader_id"),
                    informed_progress=message.get("informed_trader_progress")
                )
                responses = await self.bus.publish(event)
                return self._merge_responses(responses, {"status": "processing"})
            
            elif action_type == "cancel_order":
                event = OrderCancelledEvent(
                    order_id=message.get("order_id"),
                    trader_id=message.get("trader_id")
                )
                responses = await self.bus.publish(event)
                return self._merge_responses(responses, {"status": "processing"})
            
            elif action_type == "register_me":
                event = TraderRegisteredEvent(
                    trader_id=message.get("trader_id"),
                    trader_type=message.get("trader_type"),
                    gmail_username=message.get("gmail_username"),
                    trader_instance=message.get("trader_instance")
                )
                responses = await self.bus.publish(event)
                return self._merge_responses(responses, {"status": "registered"})
            
            elif action_type == "inventory_report":
                event = InventoryReportEvent(
                    trader_id=message.get("trader_id"),
                    shares=message.get("shares", 0),
                    cash=message.get("cash", 0)
                )
                responses = await self.bus.publish(event)
                return self._merge_responses(responses, {"status": "processed"})
            
            else:
                return {"status": "error", "message": f"Unknown message type: {action_type}"}
        
        except Exception as e:
            return {"status": "error", "message": f"Error processing message: {str(e)}"}
    
    def _merge_responses(self, responses: List[Dict], default: Dict) -> Dict:
        """Merge multiple responses into one."""
        if not responses:
            return default
        
        # Take the first non-empty response or the default
        for response in responses:
            if response and response.get("status") != "processing":
                return response
        
        return default 