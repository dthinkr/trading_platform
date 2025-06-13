import aio_pika
import json
from typing import Dict, Callable

class RabbitMQManager:
    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
        self.exchanges = {}

    async def initialize(self):
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()

    async def declare_exchange(self, exchange_name: str, exchange_type: aio_pika.ExchangeType, auto_delete: bool = True):
        exchange = await self.channel.declare_exchange(
            exchange_name, exchange_type, auto_delete=auto_delete
        )
        self.exchanges[exchange_name] = exchange
        return exchange

    async def declare_queue(self, queue_name: str, auto_delete: bool = True):
        return await self.channel.declare_queue(queue_name, auto_delete=auto_delete)

    async def bind_queue_to_exchange(self, queue_name: str, exchange_name: str):
        queue = await self.declare_queue(queue_name)
        await queue.bind(self.exchanges[exchange_name])

    async def consume(self, queue_name: str, callback: Callable):
        # Use declare_queue to ensure the queue exists and get the queue object
        queue = await self.declare_queue(queue_name)
        await queue.consume(callback)

    async def publish(self, exchange_name: str, message: Dict, routing_key: str = ""):
        exchange = self.exchanges[exchange_name]
        await exchange.publish(
            aio_pika.Message(body=json.dumps(message).encode()),
            routing_key=routing_key,
        )

    async def clean_up(self):
        for exchange in self.exchanges.values():
            await exchange.delete()
        await self.channel.close()
        await self.connection.close()