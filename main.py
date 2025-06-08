from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional, List
import mysql.connector
from mysql.connector import Error
import httpx
import logging
logging.basicConfig(level=logging.DEBUG)

# Инициализация FastAPI приложения
app = FastAPI()


# Настройка базы данных MySQL
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://isp_p_Titova:12345@77.91.86.135/store2_1"

# Инициализация компонентов безопасности
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Микросервис юзер
SERVICES = {
    "users": "http://localhost:8001",
}

# Модели данных
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    disabled: bool = False
    roles: List[str] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Блок 1. Функции для БД
def get_db_connection():
    try:
        print("Попытка подключения к MySQL с параметрами:", Config.DB_CONFIG)
        connection = mysql.connector.connect(
            host=Config.DB_CONFIG["host"],
            user=Config.DB_CONFIG["user"],
            password=Config.DB_CONFIG["password"],
            database=Config.DB_CONFIG["database"],
            port=Config.DB_CONFIG["port"],
            connect_timeout=5  
        )
        print("Подключение к MySQL успешно установлено")
        return connection
    except Error as e:
        print(f"Ошибка подключения к MySQL: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Не удалось подключиться к базе данных: {e}"
        )

def init_db():
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Таблица пользователей 
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            full_name VARCHAR(100),
            hashed_password VARCHAR(255) NOT NULL,
            disabled BOOLEAN DEFAULT FALSE
        )""")

        # Таблица ролей и разрешений
        cursor.execute("CREATE TABLE IF NOT EXISTS roles (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(50) UNIQUE NOT NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS permissions (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(50) UNIQUE NOT NULL)")
        
        # Таблицы связей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INT NOT NULL,
            role_id INT NOT NULL,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INT NOT NULL,
            permission_id INT NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles(id),
            FOREIGN KEY (permission_id) REFERENCES permissions(id)
        )""")

        # Базовые роли и разрешения
        cursor.execute("INSERT IGNORE INTO roles (name) VALUES ('admin'), ('user')")
        cursor.execute("""
        INSERT IGNORE INTO permissions (name) VALUES 
        ('users:read'), ('users:create'), ('users:update'), ('users:delete'),
        ('orders:read'), ('orders:create'), ('orders:update'), ('orders:delete')
        """)

        connection.commit()
    except Error as e:
        print(f"Ошибка инициализации БД: {e}")
        if connection:
            connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка инициализации БД: {e}"
        )
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# Доп.функции
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

# Работа с пользователями
def get_user_by_username(username: str):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
        SELECT u.*, GROUP_CONCAT(r.name) as roles
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        WHERE u.username = %s
        GROUP BY u.id
        """, (username,))
        
        user = cursor.fetchone()
        if user:
            user['roles'] = user['roles'].split(',') if user['roles'] else []
        return user
    except Error as e:
        print(f"Ошибка получения пользователя: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def create_user(user: UserCreate):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        hashed_password = get_password_hash(user.password)
        
        cursor.execute("""
        INSERT INTO users (username, email, full_name, hashed_password)
        VALUES (%s, %s, %s, %s)
        """, (user.username, user.email, user.full_name, hashed_password))
        
        user_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO user_roles (user_id, role_id)
        SELECT %s, id FROM roles WHERE name = 'user' 
        """, (user_id,))
        
        connection.commit()
        return user_id
    except Error as e:
        connection.rollback()
        print(f"Ошибка создания пользователя: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Авторизация аутентификация
def authenticate_user(username: str, password: str):
    user = get_user_by_username(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
        return get_user_by_username(username)
    except JWTError:
        raise credentials_exception

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("disabled"):
        raise HTTPException(status_code=400, detail="Неактивный пользователь")
    return current_user

def has_permission(permission: str):
    def permission_checker(current_user: dict = Depends(get_current_active_user)):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            if not current_user.get('roles'):
                raise HTTPException(status_code=403, detail="Недостаточно прав")
                
            cursor.execute("""
            SELECT COUNT(*) FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.id
            JOIN roles r ON rp.role_id = r.id
            WHERE r.name IN (%s) AND p.name = %s
            """, (','.join(current_user['roles']), permission))
            
            if not cursor.fetchone()[0]:
                raise HTTPException(status_code=403, detail="Недостаточно прав")
            return current_user
        except Error as e:
            raise HTTPException(status_code=500, detail=f"Ошибка проверки прав: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return permission_checker

# БЛОК МАРШРУТОВ 
@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/register", response_model=User, summary="Регистрация пользователя")
async def register_user(user: UserCreate):
    if get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    
    user_id = create_user(user)
    if not user_id:
        raise HTTPException(status_code=500, detail="Ошибка создания пользователя")
    
    return {**user.dict(), "id": user_id, "disabled": False, "roles": ["user"]}

@app.post("/token", response_model=Token, summary="Получение JWT токена")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User, summary="Информация о текущем пользователе")
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    return current_user

@app.post("/logout", summary="Выход из системы")
async def logout(token: str = Depends(oauth2_scheme)):
    return {"message": "Успешный выход из системы"}

@app.get("/admin/users", summary="Список всех пользователей (только для админов)")
async def get_all_users(current_user: dict = Depends(has_permission("users:read"))):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
        SELECT u.id, u.username, u.email, u.full_name, u.disabled, 
               GROUP_CONCAT(r.name) as roles
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        GROUP BY u.id
        """)
        
        users = cursor.fetchall()
        for user in users:
            user['roles'] = user['roles'].split(',') if user['roles'] else []
        
        return users
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway(request: Request, service: str, path: str):
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail="Сервис не найден")
    
    url = f"{SERVICES[service]}/{path}"
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers=dict(request.headers),
            params=dict(request.query_params),
            data=await request.body()
        )
    
    return response.json()

if __name__ == "__main__":
    # Проверка подключения к БД перед запуском
    try:
        test_conn = get_db_connection()
        if test_conn.is_connected():
            test_conn.close()
            print("Проверка подключения к БД: УСПЕШНО")
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        exit(1)

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)