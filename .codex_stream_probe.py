import asyncio
import json
import re
import time

from utils.deepseek_web import DeepSeekWebClient


def shape(value, depth=0):
    if depth > 2:
        return type(value).__name__
    if isinstance(value, dict):
        return {key: shape(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [shape(value[0], depth + 1)] if value else []
    if isinstance(value, str):
        return f"str[{len(value)}]"
    return type(value).__name__


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


async def main():
    client = DeepSeekWebClient()
    try:
        page = await client._get_page("stream-probe")
        textbox = await client._wait_for_textbox(page)
        await client._set_mode(page, "Instant")
        await client._set_toggle(page, "DeepThink", False)
        await client._set_toggle(page, "Search", True)
        started = time.monotonic()
        async with page.expect_response(
            lambda response: (
                "/api/v0/chat/completion" in response.url
                and response.request.method == "POST"
            ),
            timeout=60_000,
        ) as pending:
            await textbox.fill(
                "Who won the Argentina vs Jordan match on June 27, 2026? "
                "Reply in one sentence after searching."
            )
            await textbox.press("Enter")
        response = await pending.value
        body = await response.body()
        events = []
        for line in body.decode("utf-8", "replace").splitlines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                pass
        print(f"HTTP_STATUS={response.status}")
        print(f"CONTENT_TYPE={response.headers.get('content-type', '')}")
        print(f"BODY_SECONDS={time.monotonic() - started:.2f}")
        print(f"BODY_BYTES={len(body)}")
        print(f"EVENTS={len(events)}")
        final_contents = [
            event["content"]
            for event in events
            if isinstance(event, dict) and isinstance(event.get("content"), str)
        ]
        urls = set()
        for event in events:
            for value in strings(event):
                urls.update(re.findall(r"https?://[^\s\"'<>]+", value))
        print(f"FINAL_CONTENT_EVENTS={len(final_contents)}")
        print(f"FINAL_CONTENT_LENGTH={len(final_contents[-1]) if final_contents else 0}")
        print(f"URLS={len(urls)}")
        unique = []
        for event in events:
            item = repr(shape(event))
            if item not in unique:
                unique.append(item)
        for index, item in enumerate(unique[:12]):
            print(f"SHAPE_{index}={item}")
    finally:
        await client.close()


asyncio.run(main())
