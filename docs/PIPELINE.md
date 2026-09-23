# MEGALODON — Pipeline

```
4K Drone Video
      │
      ▼
┌─────────────────────┐
│ 01 Video Processing  │  FFmpeg probe + streamed frame extraction (OpenCV-compatible)
└─────────┬────────────┘
          ▼
┌─────────────────────┐
│ 02 Frame Analysis    │  blur / exposure / contrast / compression scoring (OpenCV)
└─────────┬────────────┘
          ▼
┌─────────────────────┐
│ 03 Keyframe Selection│  ORB similarity + Farneback motion + overlap
└─────────┬────────────┘
          ▼
┌─────────────────────────────┐
│ 04 Camera Pose               │  Visual-Inertial SLAM (ORB + 5-point VO)
│    + Scene Understanding     │  + optional GPS/IMU/RTK EKF-style fusion
└──────────┬────────────┬─────┘
           │            │
           ▼            │
┌─────────────────────┐ │
│ 05 Dynamic Object    │ │   YOLOv8 → SAM2(DEMO) → IOU tracking →
│    Handling          │ │   dynamic mask + dynamic-object layer
└─────────┬────────────┘ │
          │        ┌──────┘  (camera pose feeds both reconstruction and georeferencing)
          ▼        ▼
┌─────────────────────────────┐
│ 06 AI 3D Reconstruction       │  classical MVS triangulation (real) +
│                                │  Depth Anything V2 / VGGT-O / Speed3R (DEMO,
│                                │  substituted by the real MVS cloud, labeled)
└─────────┬──────────────────────┘
          ▼
┌─────────────────────────────┐
│ 07 3D Fusion + Optimization   │  Open3D dedup/outlier removal + Bundle
│                                │  Adjustment (scipy) + confidence tiers
└─────────┬──────────────────────┘
          ▼
┌─────────────────────────────┐
│ 08 Georeferencing             │  PROJ/pyproj ENU + Umeyama scale correction
│                                │  (or explicit LOCAL marking if no GPS)
└─────────┬──────────────────────┘
          ▼
┌─────────────────────────────┐
│ 09 Mesh + Texture             │  TSDF integration → Poisson reconstruction
│                                │  → nearest-camera texture projection
└─────────┬──────────────────────┘
          ▼
┌─────────────────────────────┐
│ 10 Final Output                │  GLB/OBJ/PLY + coordinates.json +
│    (Final Digital Twin)        │  confidence map + dynamic layer + report.json
└─────────────────────────────┘
```

## Data flow contract between stages

| Stage | Reads | Writes |
|---|---|---|
| 01 | uploaded video file | `frames/*.jpg`, `VideoMetadata` row |
| 02 | `frames/*.jpg` | `frames/quality/frame_quality.{json,csv}`, `Frame` rows |
| 03 | scored frames | `keyframes/*.jpg`, `keyframes/keyframes.json`, `Keyframe` rows |
| 04 | `keyframes/*.jpg`, optional sensor file | `pose/trajectory.json`, `Pose` rows |
| 05 | `keyframes/*.jpg` | `dynamic/detections/`, `dynamic/masks/`, `dynamic/dynamic_objects.json`, `dynamic/dynamic_layer/` |
| 06 | keyframes + poses + dynamic masks | `pointcloud/raw/mvs_raw.ply`, `depth/`, `vggt/`, `speed3r/` |
| 07 | raw point cloud | `pointcloud/fused/fused_pointcloud.ply`, `optimization/`, `confidence/` |
| 08 | fused points + poses + sensor file | `georeference/coordinates.json`, `georeference/trajectory.geojson` |
| 09 | georeferenced points + keyframes + poses | `mesh/tsdf/`, `mesh/poisson/`, `final/model.{glb,obj,ply}` |
| 10 | everything above | `final/report.json` |

Every arrow above is a real file dependency: stage *N* cannot run without
stage *N-1*'s actual output on disk, verified end-to-end in
`backend/tests/` and via a full Playwright browser run against the live
stack (upload → live WebSocket progress → completed → rendered 3D result).
