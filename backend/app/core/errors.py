from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """docs/api.md 0.3節の共通エラー形式に対応するアプリケーション例外。"""

    def __init__(
        self,
        code: str,
        status_code: int,
        message: str,
        index: int | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.message = message
        self.index = index
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "index": exc.index,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "予期しないエラーが発生しました",
                    "index": None,
                }
            },
        )
