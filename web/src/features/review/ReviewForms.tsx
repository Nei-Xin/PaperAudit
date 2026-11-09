import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { READ_ONLY, resourceUrl, send } from "@/api/client";
import { keys, useJobs } from "@/api/queries";
import type {
  ConcernUpdate,
  Job,
  PeerReviewReport,
  PeerReviewRevision,
  RelatedWorkRequest,
  ReviewConcern,
  ReviewRequest,
  Venue,
} from "@/api/types";
import { ErrorState, Progress } from "@/components/States";
import { Modal } from "@/components/Modal";
import {
  DECISION_LABELS,
  ISSUE_CATEGORY_LABELS,
  ISSUE_SEVERITY_NAMES,
  ISSUE_STATUS_LABELS,
  VENUE_LABELS,
} from "@/lib/labels";

const input = "w-full min-w-0 rounded-lg bg-page p-2 text-sm";
export const DEFAULT_WEIGHTS = {
  significance: 20,
  novelty: 20,
  soundness: 20,
  experimental_rigor: 20,
  clarity: 10,
  reproducibility: 10,
};
const dimensions: Record<string, string> = {
  significance: "重要性",
  novelty: "创新性",
  soundness: "可靠性",
  experimental_rigor: "实验充分性",
  clarity: "表达清晰度",
  reproducibility: "可复现性",
};
export function RubricFields({
  venue,
  weights,
  onVenue,
  onWeights,
}: {
  venue: Venue;
  weights: Record<string, number>;
  onVenue: (value: Venue) => void;
  onWeights: (value: Record<string, number>) => void;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-3">
      <label className="text-sm">
        评审标准
        <select
          aria-label="评审标准"
          className={input}
          value={venue}
          onChange={(e) => onVenue(e.target.value as Venue)}
        >
          {Object.entries(VENUE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
      </label>
      {venue === "custom" && (
        <fieldset className="grid grid-cols-2 gap-3">
          <legend className="mb-2 text-xs text-ink-3">
            六维权重（按比例计算，合计须大于零）
          </legend>
          {Object.keys(DEFAULT_WEIGHTS).map((k) => (
            <label key={k} className="text-xs">
              {dimensions[k]}
              <input
                className={input}
                type="number"
                min="0"
                max="100"
                step="any"
                value={weights[k] ?? 0}
                onChange={(e) =>
                  onWeights({ ...weights, [k]: Number(e.target.value) })
                }
              />
            </label>
          ))}
        </fieldset>
      )}
    </div>
  );
}

export function useRefreshProject(id: string) {
  const client = useQueryClient();
  return async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: keys.project(id) }),
      client.invalidateQueries({ queryKey: keys.projects }),
    ]);
  };
}

export function ReviewForm({
  projectId,
  report,
  onDone,
}: {
  projectId: string;
  report?: PeerReviewReport;
  onDone?: () => void;
}) {
  const [venue, setVenue] = useState<Venue>(report?.venue ?? "general_ai_ml");
  const [weights, setWeights] = useState<Record<string, number>>(
    report?.venue === "custom"
      ? Object.fromEntries(
          Object.entries(report.rubric_weights).map(([k, v]) => [k, v * 100]),
        )
      : DEFAULT_WEIGHTS,
  );
  const [ack, setAck] = useState(false);
  const refresh = useRefreshProject(projectId);
  const submit = useMutation({
    mutationFn: () =>
      send<Job>("POST", `/api/projects/${projectId}/review-jobs`, {
        venue,
        rubric_weights: venue === "custom" ? weights : {},
        privacy_ack: ack,
      } satisfies ReviewRequest),
    onSuccess: async () => {
      await refresh();
      onDone?.();
    },
  });
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (!submit.isPending) submit.mutate();
      }}
    >
      {report && (
        <p className="text-sm text-ink-3">
          完成后将更新当前评审并重置修改计划进度，已有修改稿仍保留。
        </p>
      )}
      <fieldset disabled={submit.isPending} className="flex flex-col gap-4">
        <RubricFields
          venue={venue}
          weights={weights}
          onVenue={setVenue}
          onWeights={setWeights}
        />
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-1"
            checked={ack}
            onChange={(e) => setAck(e.target.checked)}
          />
          我同意将论文文本发送到已配置的模型服务进行评审。
        </label>
      </fieldset>
      {submit.error && <ErrorState error={submit.error} />}
      <button
        className="btn-primary self-start"
        disabled={
          READ_ONLY ||
          !ack ||
          submit.isPending ||
          (venue === "custom" &&
            Object.values(weights).reduce((a, b) => a + b, 0) <= 0)
        }
      >
        {submit.isPending ? "正在提交…" : "开始模拟评审"}
      </button>
    </form>
  );
}

export function ReviewTasks({
  projectId,
  kind,
}: {
  projectId: string;
  kind: "review" | "revision";
}) {
  const jobs = useJobs(projectId);
  const refresh = useRefreshProject(projectId);
  const active = jobs.data?.[kind].find(
    (j) => j.status === "QUEUED" || j.status === "RUNNING",
  );
  const latest = jobs.data?.[kind][0];
  const failed =
    !active && latest && ["FAILED", "INTERRUPTED"].includes(latest.status)
      ? latest
      : undefined;
  const retry = useMutation({
    mutationFn: () =>
      send(
        "POST",
        `/api/projects/${projectId}/${kind === "review" ? "review" : "revision"}-jobs/${failed!.job_id}/retry`,
      ),
    onSuccess: refresh,
  });
  return (
    <>
      {jobs.error && <ErrorState error={jobs.error} />}
      {active && (
        <div role="status" className="rounded-lg bg-accent-soft p-3">
          <p className="mb-2 text-sm">
            {kind === "review" ? "评审正在后台生成" : "修改稿正在后台复审"}
          </p>
          <Progress value={active.progress} label={active.stage} />
        </div>
      )}
      {failed && (
        <div className="flex flex-col gap-2 rounded-lg bg-warn-soft p-3">
          <p role="alert" className="text-sm">
            {kind === "review" ? "评审" : "复审"}未完成：
            {failed.error || failed.stage}
          </p>
          <button
            className="btn-secondary self-start"
            disabled={READ_ONLY || retry.isPending}
            onClick={() => retry.mutate()}
          >
            {retry.isPending
              ? "正在提交…"
              : `重试${kind === "review" ? "评审" : "复审"}`}
          </button>
        </div>
      )}
      {retry.error && <ErrorState error={retry.error} />}
    </>
  );
}

export function ConcernEditor({
  projectId,
  report,
  concern,
  index,
  disabled,
}: {
  projectId: string;
  report: PeerReviewReport;
  concern: ReviewConcern;
  index: number;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        className="btn-secondary self-start"
        disabled={READ_ONLY || disabled}
        onClick={() => setOpen(true)}
      >
        人工复核
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="人工复核问题">
        <ConcernForm
          key={`${report.run_id}-${index}`}
          projectId={projectId}
          report={report}
          concern={concern}
          index={index}
          onDone={() => setOpen(false)}
        />
      </Modal>
    </>
  );
}
function ConcernForm({
  projectId,
  report,
  concern,
  index,
  onDone,
}: {
  projectId: string;
  report: PeerReviewReport;
  concern: ReviewConcern;
  index: number;
  onDone: () => void;
}) {
  const [value, setValue] = useState<ConcernUpdate>({
    expected_run_id: report.run_id,
    status: concern.status,
    severity_level: concern.severity_level,
    category: concern.category,
    support_type: concern.support_type,
    human_reviewed: concern.human_reviewed,
    human_decision: concern.human_decision,
    human_note: concern.human_note,
  });
  const refresh = useRefreshProject(projectId);
  const save = useMutation({
    mutationFn: () =>
      send(
        "PATCH",
        `/api/projects/${projectId}/review/concerns/${index}`,
        value,
      ),
    onSuccess: async () => {
      await refresh();
      onDone();
    },
  });
  const fields = [
    ["status", "处理状态", ISSUE_STATUS_LABELS],
    ["severity_level", "严重度", ISSUE_SEVERITY_NAMES],
    ["category", "问题类别", ISSUE_CATEGORY_LABELS],
    [
      "human_decision",
      "人工结论",
      {
        unreviewed: "未复核",
        confirmed: "确认问题",
        partial: "部分成立",
        false_positive: "误报",
        insufficient_evidence: "证据不足",
      },
    ],
    [
      "support_type",
      "证据判断",
      { fact: "事实", inference: "推断", insufficient_evidence: "证据不足" },
    ],
  ] as const;
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (!save.isPending) save.mutate();
      }}
    >
      <p className="text-sm font-medium">{concern.title}</p>
      <fieldset
        disabled={save.isPending}
        className="grid grid-cols-1 gap-3 sm:grid-cols-2"
      >
        {fields.map(([key, label, options]) => (
          <label key={key} className="text-sm">
            {label}
            <select
              aria-label={label}
              className={input}
              value={String(value[key] ?? "")}
              onChange={(e) => setValue({ ...value, [key]: e.target.value })}
            >
              {Object.entries(options).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        ))}
        <label className="text-sm sm:col-span-2">
          复核备注
          <textarea
            className={input}
            rows={3}
            maxLength={10000}
            value={value.human_note ?? ""}
            onChange={(e) => setValue({ ...value, human_note: e.target.value })}
          />
        </label>
        <label className="flex gap-2 text-sm">
          <input
            type="checkbox"
            checked={value.human_reviewed ?? false}
            onChange={(e) =>
              setValue({ ...value, human_reviewed: e.target.checked })
            }
          />
          已人工确认
        </label>
      </fieldset>
      {save.error && <ErrorState error={save.error} />}
      <button
        className="btn-primary self-start"
        disabled={READ_ONLY || save.isPending}
      >
        {save.isPending ? "正在保存…" : "保存人工复核"}
      </button>
    </form>
  );
}

export function RelatedWork({
  projectId,
  report,
  disabled,
}: {
  projectId: string;
  report: PeerReviewReport;
  disabled: boolean;
}) {
  const [refs, setRefs] = useState<RelatedWorkRequest["references"]>(
    report.related_work_comparison?.references.length
      ? report.related_work_comparison.references
      : [{ citation: "", url: "", distinction: "" }],
  );
  const [ack, setAck] = useState(false);
  const refresh = useRefreshProject(projectId);
  const compare = useMutation({
    mutationFn: () =>
      send("POST", `/api/projects/${projectId}/review/related-work`, {
        references: refs,
        privacy_ack: ack,
        expected_run_id: report.run_id,
      } satisfies RelatedWorkRequest),
    onSuccess: refresh,
  });
  const result = report.related_work_comparison;
  return (
    <details className="border-t border-line-soft pt-4">
      <summary className="cursor-pointer text-sm font-semibold">
        相关工作对比
      </summary>
      <form
        className="mt-3 flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!compare.isPending) compare.mutate();
        }}
      >
        <p className="text-xs text-ink-3">
          填写最多 5 篇相关工作及其区别。链接仅作为来源记录。
        </p>
        <fieldset
          disabled={compare.isPending || disabled || READ_ONLY}
          className="flex flex-col gap-3"
        >
          {refs.map((r, i) => (
            <div key={i} className="flex flex-col gap-2 rounded-lg bg-page p-3">
              <label className="text-sm">
                文献 {i + 1}
                <input
                  className={input}
                  required
                  maxLength={2000}
                  value={r.citation}
                  onChange={(e) =>
                    setRefs(
                      refs.map((v, j) =>
                        j === i ? { ...v, citation: e.target.value } : v,
                      ),
                    )
                  }
                />
              </label>
              <label className="text-xs">
                来源链接
                <input
                  className={input}
                  maxLength={2048}
                  value={r.url ?? ""}
                  onChange={(e) =>
                    setRefs(
                      refs.map((v, j) =>
                        j === i ? { ...v, url: e.target.value } : v,
                      ),
                    )
                  }
                />
              </label>
              <label className="text-xs">
                与本文的区别
                <textarea
                  className={input}
                  maxLength={10000}
                  value={r.distinction ?? ""}
                  onChange={(e) =>
                    setRefs(
                      refs.map((v, j) =>
                        j === i ? { ...v, distinction: e.target.value } : v,
                      ),
                    )
                  }
                />
              </label>
              {refs.length > 1 && (
                <button
                  type="button"
                  className="self-start text-xs text-bad"
                  onClick={() => setRefs(refs.filter((_, j) => j !== i))}
                >
                  移除此文献
                </button>
              )}
            </div>
          ))}
          {refs.length < 5 && (
            <button
              type="button"
              className="btn-secondary self-start"
              onClick={() =>
                setRefs([...refs, { citation: "", url: "", distinction: "" }])
              }
            >
              添加相关工作
            </button>
          )}
          <label className="flex items-start gap-2 text-sm">
            <input
              className="mt-1"
              type="checkbox"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
            />
            我同意将论文和相关工作信息发送到模型服务。
          </label>
        </fieldset>
        <button
          className="btn-primary self-start"
          disabled={
            READ_ONLY ||
            disabled ||
            !ack ||
            refs.some((r) => !r.citation.trim()) ||
            compare.isPending
          }
        >
          {compare.isPending ? "正在对比…" : "对比相关工作"}
        </button>
        {compare.error && <ErrorState error={compare.error} />}
      </form>
      {result && (
        <div
          className="mt-4 flex flex-col gap-2 text-sm leading-7"
          role="status"
        >
          <p>{result.assessment}</p>
          <ul className="list-disc pl-5">
            {result.distinctions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
          {result.gaps.length > 0 && (
            <>
              <strong>仍需补充</strong>
              <ul className="list-disc pl-5">
                {result.gaps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </>
          )}
          {result.warning && (
            <p className="text-xs text-ink-3">{result.warning}</p>
          )}
        </div>
      )}
    </details>
  );
}

export function Revisions({
  projectId,
  revisions,
  disabled,
}: {
  projectId: string;
  revisions: PeerReviewRevision[];
  disabled: boolean;
}) {
  const [file, setFile] = useState<File>();
  const [ack, setAck] = useState(false);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const jobs = useJobs(projectId);
  const running = jobs.data?.revision.some((j) =>
    ["QUEUED", "RUNNING"].includes(j.status),
  );
  const refresh = useRefreshProject(projectId);
  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.set("pdf", file!);
      form.set("privacy_ack", String(ack));
      return send("POST", `/api/projects/${projectId}/revisions`, form);
    },
    onSuccess: async () => {
      setFile(undefined);
      setAck(false);
      setVersion((v) => v + 1);
      await refresh();
    },
  });
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold">修改稿复审</h2>
      <p className="text-sm text-ink-3">
        保留基准评审，对比段落变化并重新评审修改稿。已有 {revisions.length} 版。
      </p>
      <ReviewTasks projectId={projectId} kind="revision" />
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!upload.isPending) upload.mutate();
        }}
      >
        <fieldset
          disabled={READ_ONLY || disabled || running || upload.isPending}
          className="flex flex-col gap-3"
        >
          <label className="text-sm">
            修改稿 PDF
            <input
              key={version}
              className="mt-2 block w-full min-w-0 text-sm"
              type="file"
              accept=".pdf"
              onChange={(e) => {
                const f = e.target.files?.[0];
                setFile(undefined);
                setError("");
                if (
                  f &&
                  (!f.name.toLowerCase().endsWith(".pdf") ||
                    f.size > 200 * 1024 * 1024)
                ) {
                  setError("请选择不超过 200MB 的 PDF。");
                  return;
                }
                setFile(f);
              }}
            />
          </label>
          <label className="flex gap-2 text-sm">
            <input
              type="checkbox"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
            />
            我同意将修改稿发送到模型服务进行复审。
          </label>
        </fieldset>
        <button
          className="btn-primary self-start"
          disabled={
            READ_ONLY ||
            disabled ||
            running ||
            !file ||
            !ack ||
            upload.isPending
          }
        >
          {upload.isPending ? "正在上传…" : "上传并复审"}
        </button>
      </form>
      {error && <ErrorState error={new Error(error)} />}{" "}
      {upload.error && <ErrorState error={upload.error} />}
      {revisions.map((r) => (
        <RevisionCard key={r.revision_id} projectId={projectId} revision={r} />
      ))}
      <a
        className="btn-secondary self-start"
        href={resourceUrl(`/api/projects/${projectId}/review/export?format=md`)}
      >
        下载 Markdown 评审
      </a>
    </div>
  );
}
function RevisionCard({
  projectId,
  revision: r,
}: {
  projectId: string;
  revision: PeerReviewRevision;
}) {
  const refresh = useRefreshProject(projectId);
  const confirm = useMutation({
    mutationFn: () =>
      send("PATCH", `/api/projects/${projectId}/revisions/${r.revision_id}`, {
        match_confirmed: !r.match_confirmed,
      }),
    onSuccess: refresh,
  });
  return (
    <article className="flex min-w-0 flex-col gap-3 rounded-lg border border-line p-4">
      <h3 className="break-all text-sm font-semibold">{r.original_filename}</h3>
      <p className="text-xs text-ink-3">
        {new Date(r.created_at).toLocaleString()} ·{" "}
        {DECISION_LABELS[r.report.decision].zh} ·{" "}
        {r.report.overall_score.toFixed(1)} / 10
      </p>
      <p className="text-sm leading-7">{r.report.decision_rationale}</p>
      <p className="text-xs">
        新增 {r.diff.added_chunks} 段 · 删除 {r.diff.removed_chunks} 段 · 变化{" "}
        {r.diff.changed_chunks} 段
      </p>
      <p className="text-sm">{r.diff.summary}</p>
      {(
        [
          ["已解决", r.resolved_concerns],
          ["仍需处理", r.remaining_concerns],
          ["新增问题", r.new_concerns],
          ["需核对匹配", r.ambiguous_matches],
        ] as const
      ).map(
        ([title, items]) =>
          items.length > 0 && (
            <div key={title} className="text-sm">
              <strong>{title}</strong>
              <ul className="list-disc pl-5">
                {items.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          ),
      )}
      <details className="text-sm">
        <summary className="cursor-pointer">查看段落差异与评审详情</summary>
        <div className="mt-2 whitespace-pre-line leading-7">
          {r.report.summary}
          <ul className="my-3 list-disc pl-5">
            {r.report.dimensions.map((d) => (
              <li key={d.name}>
                {dimensions[d.name] ?? d.name}：{d.score} / 5 · {d.rationale}
              </li>
            ))}
          </ul>
          {[...r.report.major_concerns, ...r.report.minor_concerns].map(
            (c, i) => (
              <section className="my-3" key={i}>
                <strong>{c.title}</strong>
                <p>{c.description}</p>
                <p>建议：{c.suggestion}</p>
              </section>
            ),
          )}
          {[
            ...r.diff.added_samples,
            ...r.diff.removed_samples,
            ...r.diff.changed_samples,
          ].map((s, i) => (
            <p className="mt-2 rounded bg-page p-2" key={i}>
              {s}
            </p>
          ))}
        </div>
      </details>
      <div className="flex flex-wrap gap-2">
        <a
          className="btn-secondary"
          href={resourceUrl(
            `/api/projects/${projectId}/revisions/${r.revision_id}/pdf`,
          )}
          target="_blank"
          rel="noreferrer"
        >
          查看修改稿 PDF
        </a>
        <button
          className="btn-secondary"
          disabled={READ_ONLY || confirm.isPending}
          onClick={() => confirm.mutate()}
        >
          {r.match_confirmed ? "撤销匹配确认" : "确认问题匹配"}
        </button>
      </div>
      {r.match_confirmed && (
        <p role="status" className="text-xs text-ink-3">
          已人工确认问题匹配
        </p>
      )}
      {confirm.error && <ErrorState error={confirm.error} />}
    </article>
  );
}
