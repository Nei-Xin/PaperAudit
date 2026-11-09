import { isRouteErrorResponse, Link, useRouteError } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useDocumentTitle } from "@/lib/useDocumentTitle";

/** Router errorElement: a render crash or a failed lazy chunk shows this instead of a blank page. */
export function RouteError() {
  const error = useRouteError();
  useDocumentTitle("页面出错");
  const chunkFailed = error instanceof Error && /dynamically imported module|Importing a module script failed|Failed to fetch/i.test(error.message);
  const detail = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error ? error.message : String(error);
  return (
    <div className="flex h-full min-h-[60dvh] items-center justify-center p-6">
      <div className="card flex w-full max-w-md flex-col gap-3 p-6" role="alert">
        <div className="flex items-center gap-2 text-bad-text">
          <AlertTriangle className="h-5 w-5" aria-hidden />
          <h1 className="text-lg font-semibold">{chunkFailed ? "页面资源已更新" : "页面出错了"}</h1>
        </div>
        <p className="text-sm leading-7 text-ink-3">
          {chunkFailed ? "服务已发布新版本，请重新加载页面。" : "这个页面渲染时遇到问题。可以重试，或回到首页继续。"}
        </p>
        <details className="text-xs text-ink-4">
          <summary className="cursor-pointer">错误详情</summary>
          <pre className="mt-2 whitespace-pre-wrap break-words">{detail}</pre>
        </details>
        <div className="flex gap-2">
          <button type="button" className="btn-primary" onClick={() => window.location.reload()}>重新加载</button>
          <Link to="/" className="btn-secondary" reloadDocument>返回首页</Link>
        </div>
      </div>
    </div>
  );
}
