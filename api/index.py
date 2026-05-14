"""
Vercel entry point.
Mangum wraps FastAPI (ASGI) so Vercel's serverless runtime can call it.
"""
from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
