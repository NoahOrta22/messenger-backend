# messenger_api.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from passlib.hash import bcrypt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from fastapi.responses import FileResponse

app = FastAPI()
conn = sqlite3.connect("messenger.db", check_same_thread=False)
cursor = conn.cursor()

# Serve React static files
app.mount("/static", StaticFiles(directory="build/static"), name="static")

# this is so that the backend works with the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend URL for better security
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Initialize database
def initialize_database():
    # Create the users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)
    # Create the messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    


initialize_database()

# Data model for users
class User(BaseModel):
    username: str
    password: str

# Data model for message
class Message(BaseModel):
    sender: str
    receiver: str
    message: str

# Example API endpoint
@app.get("/api/hello")
async def hello():
    return {"message": "Hello from FastAPI!"}

# Registration Endpoint
@app.post("/api/register")
def register(user: User):
    hashed_password = bcrypt.hash(user.password)
    try:
        cursor.execute("""
            INSERT INTO users (username, password)
            VALUES (?, ?)
        """, (user.username, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"message": "User registered successfully"}

# Data model for login
class LoginRequest(BaseModel):
    username: str
    password: str

# Login Endpoint
@app.post("/api/login")
def login(data: LoginRequest):
    # Debugging the input values
    print(f"Attempting to log in with Username: {data.username}, Password: {data.password}")
    cursor.execute("""
        SELECT * FROM users WHERE username = ? AND password = ?
    """, (data.username, data.password))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": f"Welcome, {data.username}!"}


@app.get("/api/users")
def get_users(exclude: str):
    cursor.execute("""
        SELECT username FROM users WHERE username != ?
    """, (exclude,))
    users = cursor.fetchall()
    return {"users": [user[0] for user in users]}


# Endpoint to send a message
@app.post("/api/send")
def send_message(msg: Message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO messages (sender, receiver, message, timestamp)
        VALUES (?, ?, ?, ?)
    """, (msg.sender, msg.receiver, msg.message, timestamp))
    conn.commit()
    return {"status": "Message sent"}

# Endpoint to retrieve messages for a specific user
@app.get("/api/messages/{user}")
def retrieve_messages(user: str, last_id: int = 0):
    cursor.execute("""
        SELECT id, sender, receiver, message, timestamp
        FROM messages
        WHERE (sender = ? OR receiver = ?) AND id > ?
        ORDER BY timestamp
    """, (user, user, last_id))
    messages = cursor.fetchall()
    return {"messages": [{"id": m[0], "sender": m[1], "receiver": m[2], "message": m[3], "timestamp": m[4]} for m in messages]}

@app.get("/")
async def serve_root():
    return FileResponse("build/index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
