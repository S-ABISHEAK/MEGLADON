export interface VideoMetadata {
  width: number | null;
  height: number | null;
  fps: number | null;
  duration: number | null;
  codec: string | null;
  bitrate: number | null;
  frame_count: number | null;
  has_gps_metadata: string | null;
}

export interface StageInfo {
  stage: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  progress: number;
  current_operation: string | null;
  stats: Record<string, any>;
  demo_mode: string | null;
  log: string;
}

export interface JobDetail {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  failed_stage: string | null;
  video_metadata: VideoMetadata | null;
  stages: StageInfo[];
}

export interface WsEvent {
  type: string;
  stage?: string;
  progress?: number;
  operation?: string;
  elapsed_s?: number;
  stats?: Record<string, any>;
  message?: string;
  component?: string;
  reason?: string;
  error?: string;
  report?: any;
  ts: number;
}

export const STAGE_LABELS: Record<string, string> = {
  VIDEO_PROCESSING: "01 Video Processing",
  FRAME_ANALYSIS: "02 Frame Analysis",
  KEYFRAME_SELECTION: "03 Keyframe Selection",
  POSE_ESTIMATION: "04 Camera Pose Estimation",
  DYNAMIC_OBJECT_HANDLING: "05 Dynamic Object Handling",
  AI_RECONSTRUCTION: "06 AI 3D Reconstruction",
  FUSION_OPTIMIZATION: "07 3D Fusion & Optimization",
  GEOREFERENCING: "08 Georeferencing",
  MESH_TEXTURE: "09 Mesh & Texture",
  FINAL_OUTPUT: "10 Final Output",
};

export const STAGE_ORDER = Object.keys(STAGE_LABELS);
