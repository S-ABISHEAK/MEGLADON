"""
Model adapter architecture (spec section 27).

Every algorithmic component of the pipeline implements one of these interfaces.
An adapter's `execute()` returns a `StageResult` that always carries `demo_mode`
(True/False) and, when True, `demo_reason` -- the pipeline must never claim a
model ran when it did not. This is the single mechanism that enforces spec
section 26 (DEMO MODE) and section 34 (no fake AI pipeline) everywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageResult:
    outputs: dict[str, Any] = field(default_factory=dict)
    demo_mode: bool = False
    demo_reason: str | None = None
    model_name: str = ""
    stats: dict[str, Any] = field(default_factory=dict)

    def label(self) -> str:
        if self.demo_mode:
            return f"{self.model_name}: DEMO ARTIFACT — {self.demo_reason}"
        return f"{self.model_name}: executed"


class Adapter:
    """Base class. Concrete adapters override `name` and the relevant method."""

    name: str = "Adapter"

    def is_available(self) -> bool:
        raise NotImplementedError

    def unavailable_reason(self) -> str:
        return "dependency unavailable in this environment"


# The following are named per spec section 27 so intent is traceable 1:1 to the PPT.
class VideoProcessor(Adapter):
    name = "FFmpeg+OpenCV VideoProcessor"

    def process_video(self, video_path: str, job_id: str) -> StageResult:
        raise NotImplementedError


class FrameAnalyzer(Adapter):
    name = "FrameAnalyzer"

    def analyze_frames(self, frame_paths: list[str]) -> StageResult:
        raise NotImplementedError


class KeyframeSelector(Adapter):
    name = "KeyframeSelector"

    def select_keyframes(self, frames: list[dict]) -> StageResult:
        raise NotImplementedError


class PoseEstimator(Adapter):
    name = "Visual-Inertial SLAM PoseEstimator"

    def estimate_pose(self, keyframes: list[dict]) -> StageResult:
        raise NotImplementedError


class SensorFusion(Adapter):
    name = "GPS/IMU/RTK SensorFusion (EKF)"

    def fuse_sensors(self, visual_poses: list[dict], sensor_file: str | None) -> StageResult:
        raise NotImplementedError


class ObjectDetector(Adapter):
    name = "YOLOv8 ObjectDetector"

    def detect_objects(self, frame_paths: list[str]) -> StageResult:
        raise NotImplementedError


class Segmenter(Adapter):
    name = "SAM2 Segmenter"

    def segment_objects(self, frame_paths: list[str], detections: list[dict]) -> StageResult:
        raise NotImplementedError


class Tracker(Adapter):
    name = "MultiObjectTracker"

    def track_objects(self, detections_per_frame: list[dict]) -> StageResult:
        raise NotImplementedError


class DepthEstimator(Adapter):
    name = "Depth Anything V2 DepthEstimator"

    def estimate_depth(self, frame_paths: list[str]) -> StageResult:
        raise NotImplementedError


class VGGTReconstructor(Adapter):
    name = "VGGT-O Reconstructor"

    def reconstruct_vggt(self, keyframes: list[dict]) -> StageResult:
        raise NotImplementedError


class Speed3RReconstructor(Adapter):
    name = "Speed3R Reconstructor"

    def reconstruct_speed3r(self, keyframes: list[dict]) -> StageResult:
        raise NotImplementedError


class MVSReconstructor(Adapter):
    name = "Multi-View Stereo (MVS)"

    def perform_mvs(self, keyframes: list[dict], poses: list[dict]) -> StageResult:
        raise NotImplementedError


class PointCloudFusion(Adapter):
    name = "Open3D PointCloudFusion"

    def fuse_pointclouds(self, point_clouds: list[dict]) -> StageResult:
        raise NotImplementedError


class BundleAdjuster(Adapter):
    name = "Bundle Adjustment / Factor Graph Optimizer"

    def optimize_geometry(self, poses: list[dict], points_path: str) -> StageResult:
        raise NotImplementedError


class Georeferencer(Adapter):
    name = "PROJ Georeferencer"

    def georeference(self, points_path: str, poses: list[dict], sensor_file: str | None) -> StageResult:
        raise NotImplementedError


class MeshGenerator(Adapter):
    name = "TSDF+Poisson MeshGenerator"

    def generate_mesh(self, points_path: str) -> StageResult:
        raise NotImplementedError


class TextureProjector(Adapter):
    name = "TextureProjector"

    def project_texture(self, mesh_path: str, keyframes: list[dict], poses: list[dict]) -> StageResult:
        raise NotImplementedError


class ConfidenceEstimator(Adapter):
    name = "ConfidenceEstimator"

    def calculate_confidence(self, points_path: str, context: dict) -> StageResult:
        raise NotImplementedError
