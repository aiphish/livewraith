#########################################################################################################
# Developed by Aiphish
# https://aiphish.ing
# https://github.com/aiphish/livewraith
#
# Example client script for creating a new Wraith on the LiveWraith server.
# Input video file should be 15-20 seconds facing the camera with a neutral 
# expression and mouth closed. Format should be mp4.
# 
#
# Use:
#   python ./create_wraith.py create video_file.mp4
#   python ./create_wraith.py status wraith_id
#   mode: 
#           create: create a new Wraith
#           status: check the status of the Wraith creation process
#
#   Wraith_id is returned from the create_wraith endpoint (see create_wraith.py).
#
#   LiveWraith API key must be stored in the environment variable LW_KEY
#
# Use of this script is subject to the Aiphish Acceptable Use Policy: https://aiphish.ing/acceptable-use
#########################################################################################################


import asyncio
import requests
import wave
import os
from uuid import UUID

import sys

tenant_id = UUID("33bc0579-1460-4a39-99b2-ab9d09b414c9") # Update/ Optional
org_id = UUID("bc5c3f22-575a-4606-b41d-ccf42a83c2ca") # Update/ Optional

api_key = os.getenv("LW_KEY")
headers = {"Authorization": f"Bearer {api_key}"}

lw_domain = "forgotten-navigation-determining-females.trycloudflare.com" # Update

def create_wraith(video_file):

    tenant_id = UUID('33bc0579-1460-4a39-99b2-ab9d09b414c9')
    org_id = UUID('bc5c3f22-575a-4606-b41d-ccf42a83c2ca')
    url = (
        f"https://{lw_domain}"
        f"/api/v1/wraith/create"
        f"?tenant_id={tenant_id}"
        f"&org_id={org_id}"
    )

    with open(video_file, 'rb') as f:
    
        files = {'video': f}
        r = requests.post(url, files=files, headers=headers)

    wraith_id = r.json()["wraith_id"]

    return wraith_id

def check_status(wraith_id):

    url = (
        f"https://{lw_domain}"
        f"/api/v1/wraith/status"
        f"?wraith_id={wraith_id}"
    )
    r = requests.get(url, headers=headers)

    return r.json()

if __name__ == "__main__":
    
    mode = sys.argv[1]

    if mode == "create":
        wraith = create_wraith(video_file=sys.argv[2])
        print(f"Wraith ID: {wraith}")
    elif mode == "status":
        status = check_status(wraith_id=sys.argv[2])
        print(f"Status: {status}")
    else:
        print("Bad mode")