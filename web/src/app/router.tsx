import { createBrowserRouter, Navigate, useParams } from "react-router-dom";
import { Shell } from "./Shell";
import { ProjectLayout } from "./ProjectLayout";
import { HomePage } from "@/features/home/HomePage";
import { ReaderPage } from "@/features/reader/ReaderPage";
import { AuditPage } from "@/features/audit/AuditPage";
import { ReviewPage } from "@/features/review/ReviewPage";
import { useProject } from "@/api/queries";
import { Loading } from "@/components/States";

/** /p/:id → the first view that has content (lecture, then audit, then review). */
function ProjectIndex() {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  if (!project.data) return <Loading />;
  const p = project.data;
  const target = p.has_learning_report ? "read" : p.has_audit ? "audit" : p.has_peer_review ? "review" : "read";
  return <Navigate to={target} replace />;
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Shell />,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: "p/:projectId",
        element: <ProjectLayout />,
        children: [
          { index: true, element: <ProjectIndex /> },
          { path: "read", element: <ReaderPage /> },
          { path: "audit/:auditId?", element: <AuditPage /> },
          { path: "review", element: <ReviewPage /> },
        ],
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
