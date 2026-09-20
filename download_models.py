from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="TMElyralab/MuseTalk",
    allow_patterns=["musetalkV15/*"],
    local_dir="/build/models",
)

snapshot_download(
    repo_id="stabilityai/sd-vae-ft-mse",
    allow_patterns=["config.json", "diffusion_pytorch_model.safetensors"],
    local_dir="/build/models/sd-vae",
)

snapshot_download(
    repo_id="openai/whisper-tiny",
    allow_patterns=["config.json", "pytorch_model.bin", "preprocessor_config.json"],
    local_dir="/build/models/whisper",
)

snapshot_download(
    repo_id="n0x1103/face-parse-bisent",
    allow_patterns=["resnet18-5c106cde.pth", "79999_iter.pth"],
    local_dir="/build/models/face-parse-bisent",
)
