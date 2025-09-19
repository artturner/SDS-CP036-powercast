"""
Minimal FastAPI app for testing Railway deployment
"""

from fastapi import FastAPI

app = FastAPI(title="Minimal Test App")

@app.get("/")
def root():
    return {"message": "Hello Railway!"}

@app.get("/health-simple")
def health():
    return {"status": "healthy"}

@app.get("/ping")
def ping():
    return {"status": "pong"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)