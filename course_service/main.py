import asyncio
import aio_pika
import json
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./courses.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100))
    description = Column(String(500))
    price = Column(Integer)

Base.metadata.create_all(bind=engine)

async def handle_request(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            action = payload.get("action")

            if action == "get_courses":
                db = SessionLocal()
                courses = db.query(Course).all()
                db.close()
                result = [
                    {"id": c.id, "title": c.title, "description": c.description, "price": c.price}
                    for c in courses
                ]
                if message.reply_to:
                    await message.channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(result).encode(),
                            correlation_id=message.correlation_id
                        ),
                        routing_key=message.reply_to
                    )
        except Exception as e:
            print(f"Failed to process course message: {e}")

async def main():
    connection = await aio_pika.connect_robust("amqp://user3:password3@localhost:5672/vhost_user3")
    channel = await connection.channel()
    queue = await channel.declare_queue("course_queue", durable=True)
    print("Course service listening on course_queue...")
    await queue.consume(handle_request)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
