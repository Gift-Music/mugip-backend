from __future__ import annotations

import uvicorn

from app import create_app
from app.settings import AppSettings

app_settings = AppSettings()


app = create_app(app_settings)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5468)
