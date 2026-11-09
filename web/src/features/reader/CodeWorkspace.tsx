import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ThemedToken } from "shiki";
import { highlightCode } from "./highlight";
import { getJson, READ_ONLY, send } from "@/api/client";
import { keys } from "@/api/queries";
import type { CodeCitation, CodeFile, CodeSelection } from "@/api/types";
import { ErrorState, Loading } from "@/components/States";

export function CodeWorkspace({
  projectId,
  hasCode,
  path,
  onPath,
  onSelect,
  onReplaced,
  citation,
  busy,
}: {
  projectId: string;
  hasCode: boolean;
  path: string;
  onPath: (p: string) => void;
  onSelect: (s: CodeSelection) => void;
  onReplaced: () => void;
  citation?: CodeCitation;
  busy: boolean;
}) {
  const client = useQueryClient();
  const [error, setError] = useState("");
  const [file, setFile] = useState<File>();
  const files = useQuery({
    queryKey: [...keys.project(projectId), "code"],
    queryFn: () => getJson<CodeFile[]>(`/api/projects/${projectId}/code/files`),
    enabled: hasCode,
  });
  const active = files.data?.find((f) => f.path === path) ?? files.data?.[0];
  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.set("code_zip", file!);
      return send("POST", `/api/projects/${projectId}/code`, form);
    },
    onSuccess: async () => {
      setFile(undefined);
      onReplaced();
      await client.invalidateQueries({ queryKey: keys.project(projectId) });
      await client.invalidateQueries({ queryKey: keys.projects });
    },
  });
  return (
    <section
      className="card flex h-full min-h-0 min-w-0 flex-col overflow-hidden"
      aria-label="代码工作区"
    >
      <div className="flex shrink-0 flex-col gap-3 border-b border-line-soft p-3">
        <h2 className="text-sm font-semibold">代码工作区</h2>
        <details open={!hasCode}>
          <summary className="cursor-pointer text-xs text-ink-3">
            {hasCode ? "替换代码 ZIP" : "上传代码 ZIP"}
          </summary>
          <form
            className="mt-2 flex flex-col gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (file && !upload.isPending) upload.mutate();
            }}
          >
            <label className="text-xs">
              源码 ZIP（最多 30MB）
              <input
                className="mt-2 block w-full min-w-0"
                type="file"
                accept=".zip"
                disabled={READ_ONLY || busy || upload.isPending}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  setFile(undefined);
                  setError("");
                  if (
                    f &&
                    (!f.name.toLowerCase().endsWith(".zip") ||
                      f.size > 30 * 1024 * 1024)
                  ) {
                    setError("请选择不超过 30MB 的 ZIP。");
                    return;
                  }
                  setFile(f);
                }}
              />
            </label>
            {hasCode && (
              <p className="text-xs text-ink-3">
                上传后替换当前代码文件；历史问答记录保留。
              </p>
            )}
            <button
              className="btn-primary self-start"
              disabled={READ_ONLY || busy || !file || upload.isPending}
            >
              {upload.isPending ? "正在上传…" : "保存代码"}
            </button>
          </form>
        </details>
        {error && <ErrorState error={new Error(error)} />}{" "}
        {upload.error && <ErrorState error={upload.error} />}
        {active && (
          <label className="text-xs">
            代码文件
            <select
              aria-label="代码文件"
              className="mt-1 w-full min-w-0 rounded bg-page p-2 text-sm"
              value={active.path}
              onChange={(e) => onPath(e.target.value)}
            >
              {files.data?.map((f) => (
                <option value={f.path} key={f.path}>
                  {f.path}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {files.isLoading ? (
        <Loading />
      ) : files.error ? (
        <ErrorState error={files.error} />
      ) : active ? (
        <CodeView
          key={`${active.path}-${active.content}`}
          file={active}
          onSelect={onSelect}
          citation={citation}
          disabled={busy || READ_ONLY}
        />
      ) : (
        <p className="p-4 text-sm text-ink-3">
          上传后可查看文件、选中代码行并结合论文提问。
        </p>
      )}
    </section>
  );
}
function CodeView({
  file,
  onSelect,
  citation,
  disabled,
}: {
  file: CodeFile;
  onSelect: (s: CodeSelection) => void;
  citation?: CodeCitation;
  disabled: boolean;
}) {
  const [range, setRange] = useState({ start: 1, end: 1 });
  const [tokens, setTokens] = useState<ThemedToken[][]>();
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let alive = true;
    highlightCode(file.content, file.language)
      .then((r) => {
        if (alive) setTokens(r);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [file]);
  useEffect(() => {
    if (citation?.path === file.path) {
      setRange({ start: citation.start_line, end: citation.end_line });
      root.current
        ?.querySelector(`[data-line="${citation.start_line}"]`)
        ?.scrollIntoView({ block: "center" });
    }
  }, [citation, file.path]);
  const lines = file.content.split("\n").slice(0, file.line_count);
  const select = () =>
    onSelect({
      path: file.path,
      start_line: range.start,
      end_line: range.end,
      text: lines
        .slice(range.start - 1, range.end)
        .join("\n")
        .slice(0, 8000),
      context_text: "",
    });
  return (
    <>
      <div className="flex shrink-0 flex-wrap items-center gap-2 p-3 text-xs">
        <label>
          起始行
          <input
            className="ml-1 w-16 rounded bg-page p-1"
            type="number"
            min={1}
            max={file.line_count}
            value={range.start}
            onChange={(e) => {
              const n = Math.max(
                1,
                Math.min(file.line_count, Number(e.target.value) || 1),
              );
              setRange({ start: n, end: Math.max(n, range.end) });
            }}
          />
        </label>
        <label>
          结束行
          <input
            className="ml-1 w-16 rounded bg-page p-1"
            type="number"
            min={range.start}
            max={file.line_count}
            value={range.end}
            onChange={(e) =>
              setRange({
                ...range,
                end: Math.max(
                  range.start,
                  Math.min(file.line_count, Number(e.target.value) || 1),
                ),
              })
            }
          />
        </label>
        <button className="btn-secondary" disabled={disabled} onClick={select}>
          就选中代码提问
        </button>
      </div>
      <div
        ref={root}
        className="min-h-0 flex-1 overflow-auto bg-white pb-4"
        tabIndex={0}
        aria-label="代码内容"
      >
        <pre className="w-max min-w-full text-[13px] leading-6">
          {lines.map((line, i) => (
            <div
              key={i}
              data-line={i + 1}
              className={
                i + 1 >= range.start && i + 1 <= range.end
                  ? "bg-accent-soft"
                  : ""
              }
            >
              <button
                className="sticky left-0 mr-3 inline-block w-12 select-none bg-page text-right text-ink-4"
                aria-label={`选择第 ${i + 1} 行`}
                onClick={(e) =>
                  setRange(
                    e.shiftKey
                      ? {
                          start: Math.min(range.start, i + 1),
                          end: Math.max(range.start, i + 1),
                        }
                      : { start: i + 1, end: i + 1 },
                  )
                }
              >
                {i + 1}
              </button>
              {tokens?.[i]
                ? tokens[i].map((t, j) => (
                    <span key={j} style={{ color: t.color }}>
                      {t.content}
                    </span>
                  ))
                : line || " "}
            </div>
          ))}
        </pre>
      </div>
    </>
  );
}
