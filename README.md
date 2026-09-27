<p>
    <img width="197" height="78" alt="2026-09-25_02-24" src="https://github.com/aiphish/livewraith/blob/main/aiphishlogo.png" />
</p>

<div align="center">
 <h1> LiveWraith </h1>
</div>

<nav>
    <h2> Contents </h2>
    <ul>
        <li><a href="#s1">What is LiveWraith?</a></li>
        <li><a href="#s2">How does it work?</a></li>
        <li><a href="#s3">Requirements</a></li>
        <li><a href="#s4">Deployment</a></li>
        <li><a href="#s5">Getting Started (Vast.ai)</a></li>
        <li><a href="#s6">Creating a Wraith (Cloned identity)</a></li>
        <li><a href="#s7">Client Connection</a></li>
        <li><a href="#s8">Endpoints</a></li>
        <li><a href="#s9">Acceptable Use</a></li>
        <li><a href="#s10">License</a></li>
    </ul>
</nav>

<h2 id="s1"> What is LiveWraith?</h2>

LiveWraith is a livestreaming service designed to add realtime likeness cloning for the Aiphish deepfake phishing platform (https://github.com/aiphish/aiphish). 

<h2 id="s2">How does it work?</h2>

LiveWraith ingests PCM_16000 audio data over a websocket connection and returns the cloned Wraith (avatar) lipsyncing to the streaming audio via a WebRTC connection.

<h2 id="s3">Requirements</h2>

LiveWraith works best on a machine with an Nvidia V100, RTX 4090, RTX 5090 or better graphics cards running CUDA 12.1.

The resulting stream is transfered via a WebRTC connection. As such, the server must accept UDP connections and be reachable for the WebRTC negotiation process (either direct or with STUN/TURN). The
LiveWraith container deployment is built with a Cloudflare tunnel if a direct WebRTC connection is not possible. This allows the service to be run on GPU rental sites such as Vast.ai. Please
see the deployment section for more information.

<h2 id="s4">Deployment</h2>

The only supported method of deployment is using the Docker container hosted at:

https://ghcr.io/aiphish/livewraith

Currently, this container only supports local storage for storing Wraiths (cloned identity files). Compatibility with remote storage is in development.

By default the container will be deployed in DEBUG mode. This can be disabled with `DEBUG=false`.

Auth is handled through a Bearer token. All requests to the server (including websocket) must include the
auth header: `Authorization: Bearer <token>`

An API key can be set in the container env variables. If the server is started in DEBUG mode, and a key is not provided, one will be generated on startup and can be found in the logs. This should not be used for production deployments. Debug logs are not sanitized.

LiveWraith must have access to the system's GPU. If running on an on-prem deployment use docker flag `-gpus=all` or declare a device.

For cloud GPU deployments, consult the providers documentation. Vast.ai, which automatically passes the GPU through to the container, is discussed below for reference.

<h2 id="s5"> Getting Started (Vast.ai)</h2>

This section details an example deployment on a <a href=https://vast.ai>vast.ai</a> GPU instance. 
This is an example setup to demonstrate how an initial deployment might look. Aiphish LiveWraith is in
no way affiliated with vast.ai. Changes to deployment requirements on vast.ai might not be reflected in this section; consult vast.ai for updated documentation. This example demonstrates how to quickly test
out LiveWraith on vast.ai and is not an example of a production ready setup.

LiveWraith transfers the deepfaked video over a WebRTC connection. The client must
be able to contact the server over UDP. At the time of writing this, vast.ai does not support direct UDP
connections. To work around this, the LiveWraith container has a Cloudflare tunnel built in that can
be enabled with the `ENABLE_TUNNEL` environment variable.

### Setting up a Vast.ai Template:

| Setting | Value |
|---|---|
| **Docker Image Path** | `ghcr.io/aiphish/livewraith:latest` |
| **Docker Options** | `-e ENABLE_TUNNEL=true` |
| **Launch Mode** | `EntryPoint` |
| **Disk Size** | A 15 second 720p reference video equates to 1-2GB per Wraith.

*Note: Disk size depends on how many Wraiths you intend to create and how long each reference video is. *

### Cloudflare Tunnel Config:

To connect to a custom Cloudflare tunnel domain, first set up the domain in your Cloudflare account. Then
connect using your token with the `TUNNEL_TOKEN` environment variable.

If no tunnel token is provided, the tunnel will default to Cloudflare's free tunnel domain which can be found in the Docker container's logs: <br>

```
2026-09-25T02:00:07Z INF +--------------------------------------------------------------------------------------------+ 
2026-09-25T02:00:07Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  | 
2026-09-25T02:00:07Z INF |  https://craft-traveler-beam-productive.trycloudflare.com                                  | 
2026-09-25T02:00:07Z INF +--------------------------------------------------------------------------------------------+
```

### Auth:

LiveWraith uses an API key to validate requests to the server for all endpoints. LiveWraith is designed to
be used as a backend service in combination with Aiphish managing authorization. For this reason, all API keys have full access to all Wraith's created on the service (no tenant or organization isolation).

API keys can be set on container startup using the `API_KEYS` environment variable which takes in a list
of keys: <br>

`docker run -e API_KEYS='["key1", "key2", "key3"]'`

If running in DEBUG mode (default setup), the container will first check this environment variable for a list of keys. If none is provided a key will be automatically generated and can be viewed in the logs:


```
2026-09-25 02:00:15 [INFO] aiphish.livewraith.main.lifespan: DEV MODE, NO API KEYS PROVIDED. GENERATING...
2026-09-25 02:00:15 [INFO] aiphish.livewraith.main.lifespan: DO NOT USE IN PRODUCTION. API_KEY: 5zaTE-Qsth6PP...........BiUmSme0
```

This mode should only be used for testing in development and not for production. 

<h2 id="s6">Creating a Wraith (Cloned Identity)</h2>

A Wraith is created using the `/wraith/create` endpoint. Lipsyncing services work by painting a 
mouth over a looped video. This looping video works best if it's 10-20 seconds of a neutral expression looking
directly at the camera with the subject's mouth closed.

This endpoint will return a Wraith ID that is used to reference the created Wraith for future live streaming
requests. While the Wraith ID is returned immediately, creation runs asynchronously in the background. The status of the Wraith creation process can be polled using the `/wraith/status` endpoint. This endpoint returns a json object:

`Status: {'status': 'ready', 'progress': 1.0, 'stage': 'All stages complete', 'stage_progress': 0.0, 'error_msg': None}`

For more information and guidance see the <a href="https://doc.aiphish.ing">docs</a>.

<h2 id="s7"> Client connection</h2>

This service is designed to work seamlessly with the Aiphish framework. If you wish to use it as a standalone service, reference scripts are provided at:  <br>
* https://github.com/aiphish/livewraith/client_examples/create_wraith.py 
* https://github.com/aiphish/livewraith/client_examples/stream_wraith.py

The example streaming script saves the generated video stream to a file.

<h2 id="s8"> Endpoints</h2>

`POST` `/api/v1/wraith/create?tenant_id={UUID|None}&org_id={UUID|None}`
- video: mp4 video file, 15-20s, used for creating the Wraith

Returns the wraith_id for the newly created Wraith. Initiates an asynchronous Wraith creation process.

`GET` `/api/v1/wraith/status?wraith_id={UUID}`

Returns the current status of the newly created Wraith.

`DELETE` `/api/v1/wraith/delete?wraith_id={UUID}&tenant_id={UUID|None}&org_id={UUID|None}`

Deletes the requested Wraith and all related files. Destructive, cannot be undone.

`POST` `/api/v1/offer?tenant_id={UUID|None}&org_id={UUID|None}`
- offer_request: | 
        ```
        class OfferRequest(BaseModel):
        """
        Format for requesting an offer:
        """
        sdp: str
        type: str
        ```
- Returns {"sdp": str, "type": str, "pc_id": UUID}

Creates the new WebRTC session.

`WS` `/api/v1/wraith/stream?pc_id={UUID}&tenant_id={UUID|None}&org_id={UUID|None}`

Initiates the websocket connection to send audio data to the server.

<h2 id="s9"> Acceptable Use</h2>

Aiphish and the LiveWraith service are legitimate security tools designed to empower security teams to protect their organizations by giving them the same tools threat actors are already using in the wild. By using any Aiphish tool, in any deployment form, you agree to our Acceptable Use Policy which explicitly prohibits targeting any individual, enterprise, organization, or entity, without their explicit, informed consent.

https://aiphish.ing/acceptable-use.

<h2 id="s10"> License</h2>

Aiphish LiveWraith is released under the AGPL-3.0 license. LiveWraith bundles other opensource code and models which users of LiveWraith must comply with such as: MuseTalk, ft-mse-vae, dwpose, S3FD, Livetalking etc.





