import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Navigate, useParams } from "react-router-dom";
import { Shell } from "./Shell";
import { ProjectLayout } from "./ProjectLayout";
import { RouteError } from "./RouteError";
import { HomePage } from "@/features/home/HomePage";
import { useProject } from "@/api/queries";
import { Loading } from "@/components/States";

// Project views pull in react-pdf / pdf.js: load them on demand so the home page stays small.
const ReaderPage = lazy(() => import("@/features/reader/ReaderPage").then((m) => ({ default: m.ReaderPage })));
const AuditPage = lazy(() => import("@/features/audit/AuditPage").then((m) => ({ default: m.AuditPage })));
const ReviewPage = lazy(() => import("@/features/review/ReviewPage").then((m) => ({ default: m.ReviewPage })));

const view = (element: ReactNode) => <Suspense fallback={<Loading />}>{element}</Suspense>;

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
    errorElement: <RouteError />,
    children: [
      {
        errorElement: <RouteError />,
        children: [
          { index: true, element: <HomePage /> },
          {
            path: "p/:projectId",
            element: <ProjectLayout />,
            children: [
              { index: true, element: <ProjectIndex /> },
              { path: "read", element: view(<ReaderPage />) },
              { path: "audit/:auditId?", element: view(<AuditPage />) },
              { path: "review", element: view(<ReviewPage />) },
            ],
          },
          { path: "*", element: <Navigate to="/" replace /> },
        ],
      },
    ],
  },
]);
