"""Mouse-selectable source-code viewer backed by a Streamlit v2 component."""

from __future__ import annotations

from typing import Any

import streamlit as st

from paperaudit.models import CodeCitation, CodeFile


_CODE_SELECTOR_HTML = """
<div class="pa-selectable-code" aria-label="可选择代码的源码阅读器"></div>
"""

_CODE_SELECTOR_CSS = """
.pa-selectable-code {
  position: relative;
  height: clamp(360px, calc(78vh - 9.5rem), 780px);
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  background: #0f172a;
  scrollbar-gutter: stable;
}
.pa-code-select-content {
  min-width: max-content;
  padding: .6rem 0;
  color: #dbeafe;
  font: 12px/1.62 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.pa-code-select-line {display:flex;padding:0 .8rem;white-space:pre;}
.pa-code-select-line:hover {background:#172554;}
.pa-code-select-line.is-active {background:rgba(250,204,21,.22);box-shadow:inset 3px 0 #facc15;}
.pa-code-select-number {
  width:3.2rem;flex:0 0 3.2rem;padding-right:.9rem;color:#64748b;text-align:right;
  user-select:none;
}
.pa-code-select-line code {color:inherit;font:inherit;white-space:pre;}
.pa-code-selection-toolbar {
  position:absolute;z-index:8;display:none;align-items:center;gap:5px;
  padding:6px;border:1px solid #334155;border-radius:8px;background:#fff;
  box-shadow:0 10px 28px rgba(15,23,42,.24);
}
.pa-code-selection-toolbar.is-visible {display:flex;}
.pa-code-selection-toolbar span {padding:0 5px;color:#64748b;font:11px/1.2 sans-serif;white-space:nowrap;}
.pa-code-selection-toolbar button {
  border:0;border-radius:5px;padding:6px 8px;background:#f1f5f9;color:#334155;
  font:600 11px/1 sans-serif;cursor:pointer;white-space:nowrap;
}
.pa-code-selection-toolbar button:hover {background:#dbeafe;color:#1d4ed8;}
"""

_CODE_SELECTOR_JS = r"""
export default function(component) {
  const { data, parentElement, setTriggerValue } = component;
  const host = parentElement.querySelector('.pa-selectable-code');
  if (!host || !data) return;
  host.replaceChildren();

  const content = document.createElement('div');
  content.className = 'pa-code-select-content';
  const lineNodes = [];
  for (const item of data.lines || []) {
    const row = document.createElement('div');
    const active = data.highlight_start && item.number >= data.highlight_start
      && item.number <= data.highlight_end;
    row.className = `pa-code-select-line${active ? ' is-active' : ''}`;
    row.dataset.line = item.number;
    const number = document.createElement('span');
    number.className = 'pa-code-select-number';
    number.textContent = item.number;
    const code = document.createElement('code');
    code.textContent = item.text || ' ';
    row.append(number, code);
    content.appendChild(row);
    lineNodes.push(row);
  }
  host.appendChild(content);

  const activeRow = lineNodes.find(row => row.classList.contains('is-active'));
  if (activeRow) {
    requestAnimationFrame(() => {
      host.scrollTop = Math.max(0, activeRow.offsetTop - host.clientHeight * 0.32);
    });
  }

  const toolbar = document.createElement('div');
  toolbar.className = 'pa-code-selection-toolbar';
  const summary = document.createElement('span');
  const explainLabel = data.content_kind === 'document' ? '解释内容' : '解释代码';
  const actions = [
    ['explain', explainLabel],
    ['relate', '对应论文'],
    ['ask', '询问 AI'],
    ['copy', '复制'],
  ];
  const buttons = actions.map(([action, label]) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.action = action;
    button.textContent = label;
    toolbar.appendChild(button);
    return button;
  });
  toolbar.prepend(summary);
  host.appendChild(toolbar);

  let payload = null;
  const hideToolbar = () => {
    payload = null;
    toolbar.classList.remove('is-visible');
  };
  const readSelection = () => {
    const root = content.getRootNode();
    return typeof root.getSelection === 'function' ? root.getSelection() : window.getSelection();
  };
  const handleSelection = event => {
    const selection = readSelection();
    if (!selection || selection.isCollapsed || !selection.rangeCount) {
      hideToolbar();
      return;
    }
    const range = selection.getRangeAt(0);
    const touched = lineNodes.filter(row => {
      try { return range.intersectsNode(row.querySelector('code')); }
      catch (_) { return false; }
    });
    if (!touched.length) {
      hideToolbar();
      return;
    }
    const rawStart = Number(touched[0].dataset.line);
    const rawEnd = Number(touched[touched.length - 1].dataset.line);
    const end = Math.min(rawEnd, rawStart + 99);
    const contextRows = (data.lines || []).filter(
      item => item.number >= rawStart && item.number <= end
    );
    const selectedText = selection.toString().replace(/\r/g, '').slice(0, 8000).trim();
    const contextText = contextRows.map(item => item.text).join('\n').slice(0, 12000);
    if (!selectedText && !contextText.trim()) {
      hideToolbar();
      return;
    }
    payload = {
      path: data.path,
      start_line: rawStart,
      end_line: end,
      text: selectedText || contextText,
      context_text: contextText,
    };
    setTriggerValue('selected', {...payload, action: 'select'});
    const usedLines = end - rawStart + 1;
    summary.textContent = rawEnd > end ? `${usedLines} 行（已截断）` : `${usedLines} 行`;
    const hostBox = host.getBoundingClientRect();
    const x = Math.max(8, Math.min(host.clientWidth - 330, (event?.clientX || hostBox.left + 20) - hostBox.left + host.scrollLeft));
    const y = Math.max(8, (event?.clientY || hostBox.top + 20) - hostBox.top + host.scrollTop + 12);
    toolbar.style.left = `${x}px`;
    toolbar.style.top = `${y}px`;
    // The confirmed selection is sent immediately. Actions are rendered in the
    // assistant panel, where they remain stable after Streamlit reruns.
  };
  const runAction = async event => {
    event.preventDefault();
    event.stopPropagation();
    if (!payload) return;
    const action = event.currentTarget.dataset.action;
    if (action === 'copy') {
      try { await navigator.clipboard.writeText(payload.text); }
      catch (_) { /* Clipboard permissions can be unavailable in embedded contexts. */ }
      return;
    }
    setTriggerValue('selected', {...payload, action});
  };

  content.addEventListener('mouseup', handleSelection);
  for (const button of buttons) {
    button.addEventListener('mousedown', event => event.preventDefault());
    button.addEventListener('click', runAction);
  }
  return () => {
    content.removeEventListener('mouseup', handleSelection);
    for (const button of buttons) button.removeEventListener('click', runAction);
  };
}
"""


_code_selector = st.components.v2.component(
    "paper_code_text_selector",
    html=_CODE_SELECTOR_HTML,
    css=_CODE_SELECTOR_CSS,
    js=_CODE_SELECTOR_JS,
    isolate_styles=False,
)


def render_selectable_code(
    source: CodeFile,
    citation: CodeCitation | None,
    *,
    key: str,
) -> dict[str, Any] | None:
    lines = source.content.splitlines() or [""]
    highlight = citation if citation is not None and citation.path == source.path else None
    result = _code_selector(
        data={
            "path": source.path,
            "content_kind": (
                "document"
                if source.language == "markdown"
                else "config"
                if source.language in {"yaml", "json", "toml"}
                else "code"
            ),
            "lines": [
                {"number": index, "text": line}
                for index, line in enumerate(lines, start=1)
            ],
            "highlight_start": highlight.start_line if highlight else None,
            "highlight_end": highlight.end_line if highlight else None,
        },
        key=key,
        height="content",
        width="stretch",
        on_selected_change=lambda: None,
    )
    selected = getattr(result, "selected", None)
    return selected if isinstance(selected, dict) else None
