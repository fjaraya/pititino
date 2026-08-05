from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import ClassVar

import pytest

from pititino.config import ModelConfig
from pititino.llm.openai import OpenAIChatClient


class CompletionHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict]] = []

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(length))
        self.__class__.requests.append(request)
        if request.get("stream"):
            chunks = [
                {"id": "chatcmpl-test", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"content": "hello "}}]},
                {"id": "chatcmpl-test", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"content": "world"}}]},
            ]
            payload = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
            encoded = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        body = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1,
            "model": request["model"],
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "hello world"},
                }
            ],
        }
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.mark.anyio
async def test_openai_client_works_against_local_compatible_http_server() -> None:
    CompletionHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), CompletionHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = ModelConfig(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="local-test",
        )
        client = OpenAIChatClient(config)

        response = await client.complete([{"role": "user", "content": "hello"}], [])
        stream = await client.stream([{"role": "user", "content": "hello"}], [])
        streamed = []
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                streamed.append(chunk.choices[0].delta.content)

        assert response.choices[0].message.content == "hello world"
        assert "".join(streamed) == "hello world"
        assert len(CompletionHandler.requests) == 2
        assert CompletionHandler.requests[1]["stream"] is True
    finally:
        server.shutdown()
        thread.join(timeout=2)
