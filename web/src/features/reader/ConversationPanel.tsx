import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { READ_ONLY, send } from "@/api/client";
import { keys, useConversations } from "@/api/queries";
import type {
  AnswerScope,
  CodeCitation,
  CodeSelection,
  Conversations,
  EvidenceAnchor,
  JointAnswer,
  PaperAnswer,
  PaperSelection,
} from "@/api/types";
import { EmptyState, ErrorState, Loading, MockNote } from "@/components/States";
import { Modal } from "@/components/Modal";
import { anchorLabel } from "@/lib/labels";
import { InvestigationTrace, VERDICTS } from "./investigation";

export function QaView({
  projectId,
  selected,
  onSelected,
  onAnchor,
  onCode,
  busy,
}: {
  projectId: string;
  selected: string | undefined;
  onSelected: (id: string | undefined) => void;
  onAnchor: (a: EvidenceAnchor) => void;
  onCode: (c: CodeCitation) => void;
  busy: boolean;
}) {
  const query = useConversations(projectId);
  const client = useQueryClient();
  const [dialog, setDialog] = useState<"rename" | "delete">();
  const [title, setTitle] = useState("");
  const active = query.data?.conversations.find(
    (c) =>
      c.conversation_id === (selected ?? query.data.active_conversation_id),
  );
  const mutate = useMutation({
    mutationFn: ({
      action,
      cid,
      name,
    }: {
      action: "create" | "activate" | "rename" | "delete";
      cid?: string;
      name?: string;
    }) =>
      send<Conversations>(
        action === "create" ? "POST" : action === "delete" ? "DELETE" : "PATCH",
        `/api/projects/${projectId}/conversations${action === "create" ? "" : `/${cid}`}`,
        action === "create"
          ? { title: "新对话" }
          : action === "activate"
            ? { activate: true }
            : action === "rename"
              ? { title: name }
              : undefined,
      ),
    onSuccess: (data) => {
      client.setQueryData(keys.conversations(projectId), data);
      onSelected(data.active_conversation_id);
      setDialog(undefined);
    },
  });
  if (query.isLoading) return <Loading />;
  if (query.error) return <ErrorState error={query.error} />;
  const history = active
    ? [...active.paper_history, ...active.joint_history]
    : [];
  const disabled = READ_ONLY || busy || mutate.isPending;
  return (
    <>
      <div className="flex shrink-0 flex-wrap gap-2 px-4 pt-3">
        <label className="min-w-0 flex-1">
          <span className="sr-only">会话</span>
          <select
            disabled={disabled}
            className="h-8 w-full rounded-lg bg-page px-2 text-sm"
            value={active?.conversation_id ?? "new"}
            onChange={(e) =>
              mutate.mutate(
                e.target.value === "new"
                  ? { action: "create" }
                  : { action: "activate", cid: e.target.value },
              )
            }
          >
            <option value="new">新对话</option>
            {query.data?.conversations.map((c) => (
              <option key={c.conversation_id} value={c.conversation_id}>
                {c.title}
              </option>
            ))}
          </select>
        </label>
        <button
          className="btn-secondary"
          disabled={disabled}
          onClick={() => mutate.mutate({ action: "create" })}
        >
          新建会话
        </button>
        <button
          className="btn-secondary"
          disabled={disabled || !active}
          onClick={() => {
            setTitle(active!.title);
            setDialog("rename");
          }}
        >
          重命名
        </button>
        <button
          className="btn-secondary"
          disabled={disabled || !active}
          onClick={() => setDialog("delete")}
        >
          删除会话
        </button>
      </div>
      {mutate.error && (
        <div className="px-4 pt-2">
          <ErrorState error={mutate.error} />
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
        {history.length === 0 ? (
          <EmptyState title="从一个具体问题开始">
            可以问方法细节、实验数字、结果原因或代码实现。
          </EmptyState>
        ) : (
          <ol className="flex flex-col gap-5">
            {history.map((item, i) => (
              <li key={i} className="flex flex-col gap-2">
                <p className="self-end rounded-xl bg-active px-3 py-2 text-sm">
                  {item.question}
                </p>
                <p className="whitespace-pre-line break-words text-sm leading-7">
                  {item.answer}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {("citations" in item
                    ? item.citations
                    : item.paper_citations
                  )?.map((a) => (
                    <button
                      key={a.chunk_id}
                      disabled={!a.page}
                      className="max-w-full rounded bg-accent-soft px-2 py-1 text-left text-xs text-accent"
                      onClick={() => onAnchor(a)}
                    >
                      {anchorLabel(a)} ↗
                    </button>
                  ))}
                  {"code_citations" in item &&
                    item.code_citations.map((c) => (
                      <button
                        className="max-w-full break-all rounded bg-accent-soft px-2 py-1 text-left text-xs text-accent"
                        key={c.chunk_id}
                        onClick={() => onCode(c)}
                      >
                        {c.path} · L{c.start_line}–{c.end_line} ↗
                      </button>
                    ))}
                </div>
                {"findings" in item && (item.findings ?? []).length > 0 && (
                  <ol className="flex flex-col gap-2">
                    {(item.findings ?? []).map((f, n) => (
                      <li
                        key={n}
                        className="rounded-lg bg-page px-3 py-2 text-sm leading-6"
                      >
                        <span
                          className={`mr-2 rounded px-1.5 py-0.5 text-xs ${VERDICTS[f.verdict].tone}`}
                        >
                          {VERDICTS[f.verdict].label}
                        </span>
                        {f.text}
                        <div className="mt-1.5 flex flex-wrap gap-1.5">
                          {(f.paper_citations ?? []).map((a, k) => (
                            <button
                              key={`p${k}`}
                              disabled={!a.page}
                              className="max-w-full rounded bg-accent-soft px-2 py-1 text-left text-xs text-accent"
                              onClick={() => onAnchor(a)}
                            >
                              {anchorLabel(a)} ↗
                            </button>
                          ))}
                          {(f.code_citations ?? []).map((c, k) => (
                            <button
                              key={`c${k}`}
                              className="max-w-full break-all rounded bg-accent-soft px-2 py-1 text-left text-xs text-accent"
                              onClick={() => onCode(c)}
                            >
                              {c.path} · L{c.start_line}–{c.end_line} ↗
                            </button>
                          ))}
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
                {"investigation" in item && item.investigation && (
                  <InvestigationTrace trace={item.investigation} />
                )}
              </li>
            ))}
          </ol>
        )}
      </div>
      <Modal
        open={!!dialog}
        onClose={() => {
          if (!mutate.isPending) setDialog(undefined);
        }}
        title={dialog === "rename" ? "重命名会话" : "删除会话"}
      >
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (active && dialog && !mutate.isPending)
              mutate.mutate({
                action: dialog,
                cid: active.conversation_id,
                name: title.trim(),
              });
          }}
        >
          {dialog === "rename" ? (
            <label className="text-sm">
              会话名称
              <input
                className="mt-2 w-full rounded bg-page p-2"
                required
                maxLength={100}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
          ) : (
            <p className="text-sm">
              删除「{active?.title}」及其全部问答记录？此操作无法撤销。
            </p>
          )}
          {mutate.error && <ErrorState error={mutate.error} />}
          <button
            className="btn-primary self-start"
            disabled={
              mutate.isPending || (dialog === "rename" && !title.trim())
            }
          >
            {dialog === "rename" ? "保存名称" : "确认删除会话"}
          </button>
        </form>
      </Modal>
    </>
  );
}

export function AskBox({
  placeholder,
  projectId,
  selected,
  onAnswered,
  selection,
  selectedCode,
  onClearPaper,
  onClearCode,
  hasCode,
  page,
  onBusy,
}: {
  placeholder: string;
  projectId: string;
  selected: string | undefined;
  onAnswered: () => void;
  selection?: PaperSelection;
  selectedCode?: CodeSelection;
  onClearPaper: () => void;
  onClearCode: () => void;
  hasCode: boolean;
  page: number;
  onBusy: (busy: boolean) => void;
}) {
  const [text, setText] = useState("");
  const [scope, setScope] = useState<AnswerScope>("auto");
  const [investigate, setInvestigate] = useState(false);
  const [pageOnly, setPageOnly] = useState(false);
  const client = useQueryClient();
  const question = useMutation({
    mutationFn: () =>
      send<PaperAnswer | JointAnswer>(
        "POST",
        `/api/projects/${projectId}/${hasCode ? "code/qa" : "qa"}`,
        {
          question: text.trim(),
          conversation_id: selected,
          ...(hasCode
            ? {
                scope,
                selected_code: selectedCode,
                selection,
                investigate: scope !== "paper" && investigate,
              }
            : {
                selection,
                page_scope: !selection && pageOnly ? page : undefined,
              }),
        },
      ),
    onMutate: () => onBusy(true),
    onSuccess: async () => {
      await client.invalidateQueries({
        queryKey: keys.conversations(projectId),
      });
      setText("");
      onClearPaper();
      onClearCode();
      onAnswered();
    },
    onSettled: () => onBusy(false),
  });
  return (
    <form
      className="shrink-0 border-t border-line-soft p-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (!READ_ONLY && text.trim() && !question.isPending) question.mutate();
      }}
    >
      <fieldset disabled={question.isPending} className="flex flex-col gap-2">
        {selection && (
          <div className="rounded-lg bg-accent-soft p-2 text-xs">
            <p className="line-clamp-3">
              第 {selection.page} 页选区：{selection.text}
            </p>
            <button
              type="button"
              className="mt-1 text-accent"
              onClick={onClearPaper}
            >
              清除原文选区
            </button>
          </div>
        )}
        {selectedCode && (
          <div className="rounded-lg bg-accent-soft p-2 text-xs">
            <p className="break-all">
              代码选区：{selectedCode.path} · L{selectedCode.start_line}–
              {selectedCode.end_line}
            </p>
            <button
              type="button"
              className="mt-1 text-accent"
              onClick={onClearCode}
            >
              清除代码选区
            </button>
          </div>
        )}
        {hasCode ? (
          <div className="flex items-center gap-2 text-xs text-ink-3">
            <label className="flex min-w-0 items-center gap-2">
              回答范围
              <select
                className="min-w-0 rounded bg-page p-1"
                value={scope}
                onChange={(e) => setScope(e.target.value as AnswerScope)}
              >
                <option value="auto">自动判断</option>
                <option value="paper">论文</option>
                <option value="code">代码</option>
                <option value="joint">论文与代码</option>
              </select>
            </label>
            <label
              className="ml-auto flex shrink-0 items-center gap-1.5"
              title="多步查找并阅读代码与论文后再回答，耗时更长"
            >
              <input
                type="checkbox"
                checked={scope !== "paper" && investigate}
                disabled={scope === "paper"}
                onChange={(e) => setInvestigate(e.target.checked)}
              />
              深度调查
            </label>
          </div>
        ) : (
          <label className="flex gap-2 text-xs text-ink-3">
            <input
              type="checkbox"
              checked={pageOnly}
              onChange={(e) => setPageOnly(e.target.checked)}
              disabled={!!selection}
            />
            仅依据当前第 {page} 页
          </label>
        )}
        <label className="flex items-center gap-2 rounded-xl bg-page py-1.5 pl-3 pr-1.5">
          <span className="sr-only">追问</span>
          <input
            aria-label="追问"
            maxLength={1000}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={placeholder}
            className="min-w-0 flex-1 bg-transparent text-sm outline-none"
          />
          <button
            className="btn-primary h-8 w-8 px-0"
            disabled={READ_ONLY || !text.trim() || question.isPending}
            aria-label="发送"
          >
            <Send className="h-4 w-4" />
          </button>
        </label>
      </fieldset>
      {question.isPending && (
        <p role="status" className="mt-2 text-xs text-ink-3">
          正在检索并生成回答…
        </p>
      )}
      {question.error && (
        <div className="mt-2">
          <ErrorState error={question.error} />
        </div>
      )}
      <MockNote />
    </form>
  );
}
