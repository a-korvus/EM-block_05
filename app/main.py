"""The main entrypoint to FastAPI app."""

import logging

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.routers.get_data import router as get_router
from app.routers.other import router as other_router

app = FastAPI(default_response_class=ORJSONResponse)

routers = [get_router, other_router]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

for router in routers:
    app.include_router(router)
