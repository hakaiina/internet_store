# Microservices Backend — Online Store

Микросервисная архитектура интернет-магазина на FastAPI + RabbitMQ.

---

## Сервисы

| Сервис             | Назначение                       |
|--------------------|----------------------------------|
| `auth_service`     | Авторизация и токены             |
| `user_service`     | CRUD по пользователю             |
| `product_service`  | Работа с товарами                |
| `order_service`    | Оформление заказов (GigaOrder)   |
| `basket_service`   | Корзина                          |
| `search_service`   | Поиск по товарам                 |
| `admin_service`    | Панель управления                |
| `notification_service` | Email-уведомления (RabbitMQ) |
| `course_service`   | RPC-сервис с курсами (пример)    |
| `gateway`          | Точка входа для всех запросов    |

---

## Запуск

> Убедитесь, что установлен Docker и Docker Compose.

```bash
docker-compose up --build
```

Открой `http://localhost:8000` — это `gateway`.

RabbitMQ Management: `http://localhost:15672`  
(default login: `user1`, password: `password1`)

---

## Тесты и вызовы

Примеры RPC-запросов через `gateway`:

```bash
curl "http://localhost:8000/api/auth/me?token=..."
curl "http://localhost:8000/api/courses"
curl -X POST http://localhost:8000/api/orders/add -H "Content-Type: application/json" -d '{
  "user_id": 1,
  "items": [{"product_name": "Book", "quantity": 2, "price": 500}]
}'
```

---

## Разработка

- Python 3.10+
- FastAPI
- RabbitMQ (`aio_pika`)
- SQLite (локально)

---

## Структура

```text
.
├── gateway/
│   ├── main.py
│   ├── requirements.txt
│   └── templates/index.html
├── auth_service/
├── user_service/
├── ...
├── docker-compose.yml
└── README.md
```