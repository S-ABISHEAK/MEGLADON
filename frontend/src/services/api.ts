import type { JobDetail, StageInfo } from "../types";

const BASE = "/api";

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json();
}

export const api = {
  createJob: () => req<{ job_id: string; status: string }>("/jobs", { method: "POST" }),

  uploadVideo: (jobId: string, file: File, onProgress?: (pct: number) => void) =>
    new Promise<{ job_id: string; metadata: any }>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${BASE}/jobs/${jobId}/upload`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress((e.loaded / e.total) * 100);
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
        else reject(new Error(xhr.responseText || xhr.statusText));
      };
      xhr.onerror = () => reject(new Error("upload failed"));
      const form = new FormData();
      form.append("file", file);
      xhr.send(form);
    }),

  uploadSensorFile: (jobId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return req(`/jobs/${jobId}/sensor-upload`, { method: "POST", body: form });
  },

  startJob: (jobId: string) => req(`/jobs/${jobId}/start`, { method: "POST" }),
  retryJob: (jobId: string) => req(`/jobs/${jobId}/retry`, { method: "POST" }),

  getJob: (jobId: string) => req<JobDetail>(`/jobs/${jobId}`),
  getStatus: (jobId: string) => req<{ status: string; error: string | null; failed_stage: string | null }>(
    `/jobs/${jobId}/status`
  ),
  getStages: (jobId: string) => req<StageInfo[]>(`/jobs/${jobId}/stages`),
  getFrames: (jobId: string) => req<any[]>(`/jobs/${jobId}/frames`),
  getKeyframes: (jobId: string) => req<any[]>(`/jobs/${jobId}/keyframes`),
  getTrajectory: (jobId: string) => req<any[]>(`/jobs/${jobId}/trajectory`),
  getDynamicObjects: (jobId: string) => req<any[]>(`/jobs/${jobId}/dynamic-objects`),
  getArtifacts: (jobId: string) => req<any[]>(`/jobs/${jobId}/artifacts`),
  getModel: (jobId: string) => req<any>(`/jobs/${jobId}/model`),
  getSystemInfo: () => req<any>("/system/info"),

  artifactUrl: (path: string) => `/artifacts/${path}`,
};
