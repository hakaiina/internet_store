
# Microservices Backend — Online Store

Микросервисная архитектура интернет-магазина на FastAPI + RabbitMQ.

---

## Сервисы

| Сервис                 | Назначение                            |
|------------------------|---------------------------------------|
| `auth_service`         | Авторизация и токены                  |
| `user_service`         | CRUD по пользователю                  |
| `product_service`      | Работа с товарами                     |
| `order_service`        | Оформление заказов                    |
| `basket_service`       | Корзина                               |
| `search_service`       | Поиск по товарам                      |
| `admin_service`        | Панель управления                     |
| `notification_service` | Email-уведомления через RabbitMQ      |
| `course_service`       | Пример RPC-сервиса: получение курсов |
| `gateway`              | Точка входа для всех HTTP-запросов   |

---

## Запуск проекта

python -m fastapi dev auth_service/main.py

После запуска:

- Gateway: [http://localhost:8000](http://localhost:8000)
- Swagger UI (документация): [http://localhost:8000/docs](http://localhost:8000/docs)
- RabbitMQ Management: [http://localhost:15672](http://localhost:15672)  
  Логин: `user3`, пароль: `password3`  
  Виртуальный хост: `/vhost_user3`

---

## Примеры вызовов

```bash
# Получение данных текущего пользователя (если токен действителен)
curl "http://localhost:8000/api/auth/me?token=..."

# Получение списка курсов через RPC
curl "http://localhost:8000/api/courses"

# Добавление заказа
curl -X POST http://localhost:8000/api/orders/add   -H "Content-Type: application/json"   -d '{
    "user_id": 1,
    "items": [{"product_name": "Book", "quantity": 2, "price": 500}]
  }'
```

---

## Переменные окружения

Файл `.env` содержит:

```
RABBITMQ_URL=amqp://user3:password3@rabbitmq:5672/vhost_user3
```

Убедитесь, что все сервисы используют эту переменную для подключения к RabbitMQ.

---

## Разработка

- Python 3.10+
- FastAPI
- RabbitMQ (через `aio_pika`)
- SQLite (локально)
- Взаимодействие сервисов через очереди (RPC и events)

---

## Структура проекта

```text
.
├── gateway/
│   ├── main.py
│   ├── requirements.txt
│   └── templates/index.html
├── auth_service/
├── user_service/
├── product_service/
├── order_service/
├── basket_service/
├── admin_service/
├── search_service/
├── notification_service/
├── course_service/
├── docker-compose.yml
├── .env
└── README.md
```
