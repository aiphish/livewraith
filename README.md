<img width="197" height="78" alt="2026-09-25_02-24" src="https://github.com/user-attachments/assets/06ca5689-c6ba-4e19-8d8d-324d77cefb07" />

# LiveWraith

### What is LiveWraith?

LiveWraith is a livestreaming service designed to add realtime likeness cloning for the Aiphish deepfake phishing platform (https://github.com/aiphish/aiphish). 

### How does it work?

LiveWraith injests PCM_16000 audio data over a websocket connection and returns a WebRTC feed of the cloned Wraith (avatar) lipsyncing to the streaming audio.

### Requirements

LiveWraith works best on a machine with nvidia V100, RTX 4090, RTX 5090 or better graphics cards running CUDA 12.1.

The resulting stream is transfered via a WebRTC connection. As such, the server must accept UDP connections and be reachable for the WebRTC negotiation process (either direct or with STUN/TURN). The
LiveWraith container deployment is built with a Cloudflare tunnel that can be enabled with ENABLE_TUNNEL=true. This allows the service to be run on GPU rental sites such as Vast.ai. Please
see the deployment section for more information.

### Deployment

The only supported method of deployment is using the Docker container hosted at:

https://ghcr.io/aiphish/livewraith

Currently, this container only uses local storage for storing Wraiths (cloned identity files). Comaptibility with remote storage is in development.

By default the container will be deployed in DEBUG mode. This can be disabled with:

DEBUG=false

Auth is handled through an Bearer token. All requests to the server (including websocket) must include the
auth header:
Authorization Bearer <token>

An API key can be set in the container parameters. If the server is started in DEBUG mode, and a key is not provided, one will be generated on startup and can be found in the logs. This should not be used for production deployments. Debug logs are not sanitized.

LiveWraith must have access to the system's GPU. If running on an on-prem deployment use docker flag:

-gpus=all or declare a device.

For cloud GPU deployments, consult the providers documentation. Vast.ai, which automatically passes the GPU through to the container, is discussed below for reference.

#### Vast AI

Template Setup:

Docker Image Path: ghcr.io/aiphish/livewraith:latest
Docker Options: -e ENABLE_TUNNEL=true
Launch Mode: EntryPoint
Disk Size: Depends on how many Wraiths you intend to create and how long each reference video is. Aiphish uses a 15 second 720p reference video which equates to 1-2GB per Wraith.

## Client connection:

This service is designed to work seamlessly with the Aiphish framework. If you wish to use it as a standalone service, reference scripts are provided at:
https://github.com/aiphish/livewraith/client_examples/create_wraith.py
https://github.com/aiphish/livewraith/client_examples/stream_wraith.py

This streaming script saves the generated video stream to a file.


### Acceptable Use

Aiphish and the LiveWraith service are legitimate security tools designed to empower security teams to protect their organizations by giving them the same tools threat actors are already using in the wild. By using any Aiphish tool, in any deployment form, you agree to our Acceptable Use Policy which explicitly prohibits targeting any individual, enterprise, organization, or entity, without their explicit, informed consent.

https://aiphish.ing/acceptable-use.





