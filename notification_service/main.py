import asyncio
import aio_pika
import json

QUEUE_NAME = "notification_queue"

async def handle_notification(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            notif_type = payload.get("type")
            if notif_type == "email":
                print(f"📨 Email to {payload.get('to')}: {payload.get('subject')}")
            elif notif_type == "sms":
                print(f"📱 SMS to {payload.get('to')}: {payload.get('text')}")
            else:
                print(f"🔔 Unknown notification: {payload}")
        except Exception as e:
            print(f"❌ Failed to process message: {e}")

async def main():
    connection = await aio_pika.connect_robust("amqp://user3:password3@localhost:5672/vhost_user3")
    channel = await connection.channel()
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    print("📡 Notification service listening...")
    await queue.consume(handle_notification)
    await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
