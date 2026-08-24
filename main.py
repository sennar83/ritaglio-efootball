from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def home():
    return {
        "status": "online",
        "port": os.environ.get("PORT"),
        "message": "Render funziona correttamente"
    }

@app.get("/status")
def status():
    return {
        "server": "online"
    }
