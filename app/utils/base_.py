from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.context import AppContext
    from app.settings import AppSettings

    from . import AppUtils


@dataclasses.dataclass
class AppUtilBase:
    app_context: AppContext

    @property
    def app_settings(self) -> AppSettings:
        return self.app_context.app_settings

    @property
    def app_utils(self) -> AppUtils:
        return self.app_context.app_utils
