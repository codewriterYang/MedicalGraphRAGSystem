#!/usr/bin/env python3
# coding: utf-8
"""
会话与多轮对话辅助。

通过 LangGraph MemorySaver + 固定 thread_id 在同一会话内保留 chat_history。
"""
from __future__ import annotations

import re
from typing import Any

DEFAULT_CLI_SESSION = "cli-session"
DEFAULT_WEB_SESSION = "web-session"
DEFAULT_API_SESSION = "api-session"

MAX_HISTORY_MESSAGES = 20

# 指代词列表：当前问题以这些词开头时，通常是对上文的延续性提问
_ANAPHORA_PATTERNS = re.compile(
    r"^(那|那么|还有|另外|此外|这个|它|这些|那些|该|此|上面|刚才|之前)"
)

# 中文标点/停用词，用于从历史问题中提取关键实体词
_SEPARATOR_PATTERN = re.compile(r"[，。；！？、：""''（）\(\)\[\]【】\s,\.;!?\"'()\[\]{}]+")


def _extract_keywords_from_history(chat_history: list[dict] | None) -> list[str]:
    """
    从对话历史中提取最近一轮用户问题中的关键词（名词短语）。

    策略：取最近一条 user 消息，通过简单的分词（按标点/空格切割）
    过滤掉指代词、单字词、常见停用词，保留可能为实体的词。
    """
    if not chat_history:
        return []

    # 找到最近一条用户消息
    recent_user_text = ""
    for msg in reversed(chat_history):
        if msg.get("role") == "user":
            recent_user_text = str(msg.get("content", ""))
            break

    if not recent_user_text:
        return []

    # 简单停用词（医疗场景常见高频词）
    _STOP_WORDS = {
        "的", "了", "呢", "吗", "啊", "吧", "是", "有", "在", "和", "与", "或",
        "我", "你", "他", "她", "它", "们", "这", "那", "什么", "怎么", "如何",
        "哪些", "可以", "应该", "需要", "注意", "没有", "还是", "问问", "请问",
        "一下", "谢谢", "怎么办", "为什么会", "是什么", "要注意", "能不能",
        "会不会", "要不要", "有什么", "是什么", "怎么",
    }

    # 按分隔符切割
    words = [w.strip() for w in _SEPARATOR_PATTERN.split(recent_user_text) if w.strip()]
    # 过滤：长度>=2，非停用词，非纯数字
    keywords = [
        w for w in words
        if len(w) >= 2
        and w not in _STOP_WORDS
        and not w.isdigit()
        and not re.fullmatch(r"[0-9百千万亿]+", w)
    ]

    # 返回最可能的实体词（通常第一个就是核心实体，如"感冒"）
    return keywords[:5]  # 最多取5个关键词


def make_thread_config(session_id: str | None = None, callbacks: Any = None) -> dict:
    """构建 LangGraph 执行 config（含 thread_id）。"""
    sid = (session_id or DEFAULT_API_SESSION).strip() or DEFAULT_API_SESSION
    cfg: dict = {"configurable": {"thread_id": sid}}
    if callbacks:
        cfg["callbacks"] = callbacks
    return cfg


def enrich_question_with_history(question: str, chat_history: list[dict] | None) -> str:
    """
    将对话历史中的关键实体拼入当前问题，帮助分析节点理解指代。

    策略：
    1. 如果当前问题是指代式提问（如"那饮食上要注意什么？"），
       且历史中有实体词（如"感冒"），则将实体拼入当前问题开头：
       "感冒" + "那饮食上要注意什么？" → "感冒 饮食上要注意什么？"
    2. 如果当前问题不包含指代词，但历史非空，则仍将最近历史拼为上下文，
       供 LLM 在分析时理解背景。
    3. 如果没有历史，保持原问题不变。

    注意：不修改 state["question"]，只影响分析节点的输入文本。
    不改变路由/Cypher 规则。
    """
    if not chat_history:
        return question

    # 策略1: 指代词检测 + 历史实体拼接
    # 如果当前问题以指代词开头（如"那/还有/它"），尝试从历史中提取实体并前置
    ana_match = _ANAPHORA_PATTERNS.match(question.strip())
    if ana_match:
        keywords = _extract_keywords_from_history(chat_history)
        if keywords:
            # 去除指代词，将历史实体前置
            remaining = question[ana_match.end():].strip()
            prefix = " ".join(keywords)
            enriched = f"{prefix} {remaining}" if remaining else f"{prefix}"
            return enriched

    # 策略2: 非指代式提问但有历史 — 将最近的 user/assistant 作为上下文拼入
    recent = chat_history[-6:]
    lines = [f"{m.get('role', 'user')}: {str(m.get('content', ''))[:300]}" for m in recent]
    return (
        "【对话历史（供理解上下文，请仍针对当前问题作答）】\n"
        + "\n".join(lines)
        + f"\n【当前问题】\n{question}"
    )


def append_chat_turn(
    history: list[dict] | None,
    question: str,
    answer: str,
) -> list[dict]:
    """追加一轮 user/assistant 消息，并截断长度。"""
    hist = list(history or [])
    hist.append({"role": "user", "content": question})
    hist.append({"role": "assistant", "content": answer})
    return hist[-MAX_HISTORY_MESSAGES:]
