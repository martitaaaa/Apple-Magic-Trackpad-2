from trackpad import Trackpad
import asyncio
import websockets
import json

trackpad = Trackpad()
# trackpad.debug = True


async def send_message(websocket, path):
    cleaner = False
    while True:
        # try:
        payload = []
        if not trackpad.trackpadInfo.getCoords(0)[0] == None:
            cleaner = False
            for index in range(5):
                coords = trackpad.trackpadInfo.getCoords(index)
                if not coords[0] == None and not coords[1] == None:
                    payload.append(
                        (coords[0], coords[1], trackpad.trackpadInfo.getSurface(index)))
            if len(payload) > 0:
                await websocket.send(json.dumps(payload))
        else:
            if not cleaner:
                await websocket.send("{}")
                cleaner = True
        await asyncio.sleep(0.01)  # Send a message every 5 seconds
        # except:
        #     None

# Listen on all available network interfaces, port 8000
start_server = websockets.serve(send_message, "350z.local", 8000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
