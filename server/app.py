from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from manage_ai_config import (AIConfig, delete_config, load_config,
                              normalize_url, save_config, test_connectivity)

app = FastAPI(title="AI 配置服务", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AIConfigPayload(BaseModel):
    url: str = Field(..., description="API 请求 URL")
    key: str = Field(..., description="API Key")
    model: str = Field(..., description="模型名称")
    timeout: Optional[float] = Field(default=None, description="超时时间")
    dev_document: Optional[str] = Field(default=None, description="开发文档链接")

    def to_dataclass(self) -> AIConfig:
        return AIConfig(
            key=self.key,
            url=normalize_url(self.url),
            model=self.model,
            timeout=self.timeout or 10.0,
            dev_document=self.dev_document,
        )


class TestResponse(BaseModel):
    ok: bool
    message: str


@app.get("/api/ai-config", response_model=Optional[AIConfigPayload])
def get_config():
    config = load_config()
    if config is None:
        return None
    return AIConfigPayload(
        url=config.url,
        key=config.key,
        model=config.model,
        timeout=config.timeout,
        dev_document=config.dev_document,
    )


@app.put("/api/ai-config", response_model=AIConfigPayload)
def put_config(payload: AIConfigPayload):
    config = payload.to_dataclass()
    save_config(config)
    return payload


@app.post("/api/ai-config/test", response_model=TestResponse)
def post_test(payload: AIConfigPayload):
    config = payload.to_dataclass()
    ok, message = test_connectivity(config)
    return TestResponse(ok=ok, message=message)


@app.delete("/api/ai-config", response_model=dict)
def delete_ai_config():
    deleted = delete_config()
    if not deleted:
        raise HTTPException(status_code=404, detail="当前没有已保存的配置")
    return {"status": "deleted"}
