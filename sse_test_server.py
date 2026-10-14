import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse
import uvicorn
import threading
import time

app = FastAPI()
queues = []

@app.get("/api/events")
async def sse():
    queue = asyncio.Queue()
    queues.append(queue)
    async def event_generator():
        try:
            while True:
                data = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield {"data": data}
        except asyncio.TimeoutError:
            yield {"event": "heartbeat", "data": "ping"}
        except asyncio.CancelledError:
            pass
        finally:
            queues.remove(queue)
    return EventSourceResponse(event_generator())

def broadcast_mock():
    time.sleep(2)
    print("Broadcasting mock job...")
    # We need to push to the event loop of the running app
    # This is a simplification for the test
    for q in queues:
        # In a real app we use loop.call_soon_threadsafe
        # Here we'll just assume the loop is accessible or use a simpler mechanism
        pass

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
