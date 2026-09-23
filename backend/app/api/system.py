from fastapi import APIRouter

from app.utils.device import DEVICE

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/info")
def system_info():
    return {
        "gpu": {
            "cuda_available": DEVICE.cuda_available,
            "gpu_name": DEVICE.gpu_name,
            "vram_mb": DEVICE.gpu_memory_mb,
        },
        "cpu": DEVICE.cpu,
        "ram_gb": DEVICE.ram_gb,
        "dependencies": {
            "torch": DEVICE.torch_available,
            "ffmpeg": DEVICE.ffmpeg_available,
            "open3d": DEVICE.open3d_available,
            "ultralytics_yolov8": DEVICE.ultralytics_available,
            "sam2": DEVICE.sam2_available,
            "transformers_depth_anything_v2": DEVICE.transformers_available,
        },
        "notes": DEVICE.notes,
    }
