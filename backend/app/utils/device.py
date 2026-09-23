"""GPU/CPU capability detection (spec section 24). Runs once at process startup."""
import platform
import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class DeviceInfo:
    cuda_available: bool = False
    gpu_name: str | None = None
    gpu_memory_mb: int | None = None
    cpu: str = platform.processor() or platform.machine()
    ram_gb: float | None = None
    torch_available: bool = False
    ffmpeg_available: bool = False
    open3d_available: bool = False
    ultralytics_available: bool = False
    sam2_available: bool = False
    transformers_available: bool = False
    notes: list[str] = field(default_factory=list)


def detect_device() -> DeviceInfo:
    info = DeviceInfo()

    try:
        import torch

        info.torch_available = True
        info.cuda_available = torch.cuda.is_available()
        if info.cuda_available:
            info.gpu_name = torch.cuda.get_device_name(0)
            info.gpu_memory_mb = int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
        else:
            info.notes.append("torch installed but CUDA not available -- running on CPU")
    except ImportError:
        info.notes.append("torch not installed")

    try:
        import psutil

        info.ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        pass

    info.ffmpeg_available = shutil.which("ffmpeg") is not None
    if not info.ffmpeg_available:
        info.notes.append("ffmpeg binary not found on PATH")

    try:
        import open3d  # noqa: F401

        info.open3d_available = True
    except ImportError:
        info.notes.append("open3d not installed")

    try:
        import ultralytics  # noqa: F401

        info.ultralytics_available = True
    except ImportError:
        info.notes.append("ultralytics (YOLOv8) not installed")

    try:
        import sam2  # noqa: F401

        info.sam2_available = True
    except ImportError:
        info.notes.append("sam2 not installed -- SAM2 stage will run in DEMO MODE")

    try:
        import transformers  # noqa: F401

        info.transformers_available = True
    except ImportError:
        info.notes.append("transformers not installed -- Depth Anything V2 will run in DEMO MODE")

    return info


DEVICE = detect_device()
