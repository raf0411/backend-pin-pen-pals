"""Compatibility entry point for running the API from the project root."""

from app.main import app

if __name__ == "__main__":
    import uvicorn

    print("\n✦  WritingsReader API starting on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
