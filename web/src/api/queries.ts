import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJson, send } from "./client";
import type {
  AuditDetail, AuditRecord, Conversations, LearningReport, ProjectDetail,
  ProjectJobs, ProjectSummary, ReviewPayload, ReviewProgress, Settings,
} from "./types";

export const keys = {
  settings: ["settings"] as const,
  projects: ["projects"] as const,
  project: (id: string) => ["project", id] as const,
  lecture: (id: string) => ["project", id, "lecture"] as const,
  conversations: (id: string) => ["project", id, "conversations"] as const,
  audits: (id: string) => ["project", id, "audits"] as const,
  audit: (id: string, auditId: string) => ["project", id, "audits", auditId] as const,
  review: (id: string) => ["project", id, "review"] as const,
  jobs: (id: string) => ["project", id, "jobs"] as const,
};

export const useSettings = () => useQuery({ queryKey: keys.settings, queryFn: () => getJson<Settings>("/api/settings") });
export const useStorage = () =>
  useQuery({ queryKey: ["storage"], queryFn: () => getJson<{ name: string; path: string }>("/api/storage") });
export const useProjects = () => useQuery({ queryKey: keys.projects, queryFn: () => getJson<ProjectSummary[]>("/api/projects") });
export const useProject = (id: string) =>
  useQuery({ queryKey: keys.project(id), queryFn: () => getJson<ProjectDetail>(`/api/projects/${id}`) });
export const useLecture = (id: string) =>
  useQuery({ queryKey: keys.lecture(id), queryFn: () => getJson<LearningReport | null>(`/api/projects/${id}/lecture`) });
export const useConversations = (id: string) =>
  useQuery({ queryKey: keys.conversations(id), queryFn: () => getJson<Conversations>(`/api/projects/${id}/conversations`) });
export const useAudits = (id: string) =>
  useQuery({ queryKey: keys.audits(id), queryFn: () => getJson<AuditRecord[]>(`/api/projects/${id}/audits`) });
export const useAudit = (id: string, auditId: string | undefined) =>
  useQuery({
    queryKey: keys.audit(id, auditId ?? ""),
    queryFn: () => getJson<AuditDetail>(`/api/projects/${id}/audits/${auditId}`),
    enabled: Boolean(auditId),
  });
export const useReview = (id: string) =>
  useQuery({ queryKey: keys.review(id), queryFn: () => getJson<ReviewPayload | null>(`/api/projects/${id}/review`) });

const ACTIVE = new Set(["QUEUED", "RUNNING"]);
export function hasActiveJob(jobs: ProjectJobs | undefined): boolean {
  if (!jobs) return false;
  return [...jobs.audit, ...jobs.learning, ...jobs.review, ...jobs.revision].some((job) => ACTIVE.has(job.status));
}
/** Polls every 2s only while a background job is queued or running. */
export const useJobs = (id: string) =>
  useQuery({
    queryKey: keys.jobs(id),
    queryFn: () => getJson<ProjectJobs>(`/api/projects/${id}/jobs`),
    refetchInterval: (query) => (hasActiveJob(query.state.data) ? 2000 : false),
  });

export function useSaveReviewProgress(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (progress: ReviewProgress) => send<ReviewProgress>("PUT", `/api/projects/${id}/review/progress`, progress),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.review(id) }),
  });
}

export function useDeleteProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => send<void>("DELETE", `/api/projects/${id}`),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.projects }),
  });
}
