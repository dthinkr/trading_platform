import json
import aio_pika
from datetime import datetime
from structures.structures import Message
from main_platform.utils import CustomEncoder


class MessageBroker:
    def __init__(self, channel):
        self.channel = channel

    async def send_message(self, queue_name, message, routing_key=""):
        message = self.prepare_message(message)
        exchange = await self.channel.get_exchange(queue_name)
        await exchange.publish(
            aio_pika.Message(body=json.dumps(message, cls=CustomEncoder).encode()),
            routing_key=routing_key,
        )

    async def broadcast_message(self, base_message, exchange_name, context):
        message = self.prepare_message(base_message, context)
        exchange = await self.channel.get_exchange(exchange_name)
        await exchange.publish(
            aio_pika.Message(body=json.dumps(message, cls=CustomEncoder).encode()),
            routing_key="",
        )

    def prepare_message(self, base_message, context):
        # Update the message with additional context
        base_message.update(
            {
                "order_book": context["order_book"],
                "active_orders": context["active_orders"],
                "history": context["history"],
                "spread": context["spread"],
                "midpoint": context["midpoint"],
                "transaction_price": context["transaction_price"],
                "incoming_message": context["incoming_message"],
            }
        )
        base_message["timestamp"] = datetime.now().isoformat()
        return base_message

    async def log_message(self, trading_session_id, message_content):
        message_document = Message(
            trading_session_id=trading_session_id, content=message_content
        )
        await message_document.save_async()
