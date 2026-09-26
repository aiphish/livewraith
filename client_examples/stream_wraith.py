#########################################################################################################
# Developed by Aiphish
# https://aiphish.ing
# https://github.com/aiphish/livewraith
#
# Example client script for streaming to and from the LiveWraith server.
# Audio data is streamed to the websocket connection while audio and video are recieved
# on the WebRTC connection.

# Audio file format should be wav file with a 16kHz sample rate.
#
# Use:
#   python ./stream_wraith.py audo_input.wav output_file.mp4 wraith_id
#   Where wraith_id is returned from the create_wraith endpoint (see create_wraith.py).
#   LiveWraith API key must be stored in the environment variable LW_KEY
#
# Use of this script is subject to the Aiphish Acceptable Use Policy: https://aiphish.ing/acceptable-use
#########################################################################################################

import asyncio
import requests
import wave
import os
from websockets.asyncio.client import connect as wsconnect
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRecorder
from uuid import UUID

import sys

tenant_id = UUID('33bc0579-1460-4a39-99b2-ab9d09b414c9') # Update/ Optional
org_id = UUID('bc5c3f22-575a-4606-b41d-ccf42a83c2ca') # Update/ Optional
api_key = os.getenv("LW_KEY")
headers = {"Authorization": f"Bearer {api_key}"}

lw_domain = "forgotten-navigation-determining-females.trycloudflare.com" # Update

async def stream_audio_to_ws(pc_id, audio_file):
    uri = (
        f'wss://{lw_domain}/api/v1/wraith/stream'
        f"?pc_id={pc_id}"
        f"&tenant_id={tenant_id}"
        f"&org_id={org_id}"
    )

    async with wsconnect(uri, additional_headers=headers) as ws:
        with wave.open(audio_file, "rb") as wf:
            frames_per_chunk = wf.getframerate() // 10
            while chunk := wf.readframes(frames_per_chunk):
                await ws.send(chunk)

async def webrtc_offer(output_file, wraith_id):
    recorder = MediaRecorder(output_file)
    print("Saving to:", output_file)

    pc = RTCPeerConnection()
    pc.addTransceiver("audio", direction="recvonly")
    pc.addTransceiver("video", direction="recvonly")

    @pc.on("track")
    def on_track(track):
        recorder.addTrack(track)

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    offer_data = {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }

    offer_url=(
        f"https://{lw_domain}/api/v1/offer"
        f"?wraith_id={wraith_id}"
        f"&tenant_id={tenant_id}"
        f"&org_id={org_id}"
    )

    r = requests.post(offer_url, json=offer_data, headers=headers)
    answer = r.json()

    await pc.setRemoteDescription(
        RTCSessionDescription(
            sdp=answer["sdp"],
            type=answer["type"]
        )
    )
    await recorder.start() 
    return pc, recorder, answer["pc_id"]

async def main(audio_file, output_file, wraith_id):

    pc, recorder, pc_id = await webrtc_offer(output_file=output_file, wraith_id=wraith_id)

    ws_task = asyncio.create_task(
        stream_audio_to_ws(pc_id=pc_id, audio_file=audio_file)
    )

    try:
        await asyncio.gather(ws_task, asyncio.sleep(30))
    finally:
        await recorder.stop()
        await pc.close()
    
if __name__ == "__main__":

    asyncio.run(
        main(
            audio_file=sys.argv[1],
            output_file=sys.argv[2],
            wraith_id=sys.argv[3]
        )
    )