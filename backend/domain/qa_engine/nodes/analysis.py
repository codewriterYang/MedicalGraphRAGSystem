#!/usr/bin/env python3
# coding: utf-8
"""
问题分析节点模块。

包含三级降级分析函数：
- Level 1: 全 LLM 分析（意图 + 实体均由 LLM 提供）
- Level 2: LLM 实体 + 关键词意图（LLM 意图识别失败时）
- Level 3: 词典 NER + 关键词意图（LLM 完全不可用时）
"""
import logging

from ..state import QAState
from ..session import enrich_question_with_history

# 全局日志
log = logging.getLogger("qa_engine")

# 模块级单例（延迟初始化）
_llm_engine = None
_normalizer = None


def _init_dependencies():
    """延迟初始化依赖模块。"""
    global _llm_engine, _normalizer
    if _llm_engine is None:
        from backend.domain.kbqa.llm_engine import LLMEngine
        from backend.domain.kbqa.entity_normalizer import EntityNormalizer
        _llm_engine = LLMEngine()
        _normalizer = EntityNormalizer()


def _keyword_classify(question: str, entity_types: set[str]) -> list[str]:
    """基于关键词的意图分类。"""
    keyword_lists = _build_keyword_lists()
    question_lower = question.lower()
    matched_intents = []
    
    intent_priority = []
    if "disease" in entity_types:
        intent_priority = list(keyword_lists.keys())
    elif "symptom" in entity_types:
        intent_priority = ["symptom_disease", "disease_symptom"]
    elif "food" in entity_types:
        intent_priority = ["food_do_disease", "food_not_disease"]
    elif "check" in entity_types:
        intent_priority = ["check_disease", "disease_check"]
    else:
        intent_priority = list(keyword_lists.keys())
    
    for intent in intent_priority:
        keywords = keyword_lists.get(intent, [])
        for keyword in keywords:
            if keyword.lower() in question_lower:
                if intent not in matched_intents:
                    matched_intents.append(intent)
                break
    
    if not matched_intents:
        if "disease" in entity_types:
            matched_intents = ["disease_symptom"]
        elif "symptom" in entity_types:
            matched_intents = ["symptom_disease"]
        else:
            matched_intents = ["disease_symptom"]
    
    return matched_intents


def _build_keyword_lists() -> dict[str, list[str]]:
    """构建意图关键词列表。"""
    return {
        "disease_symptom": ["症状", "表现", "有什么症状", "会怎么样", "会怎样"],
        "symptom_disease": ["原因", "引起", "会导致", "什么病", "什么疾病"],
        "disease_cause": ["原因", "病因", "怎么得的", "怎么引起"],
        "disease_acompany": ["并发症", "伴随", "同时", "还有什么"],
        "disease_do_food": ["宜吃", "可以吃", "吃好", "有益", "推荐吃"],
        "disease_not_food": ["忌口", "不能吃", "不要吃", "少吃", "少吃"],
        "disease_check": ["检查", "做什么检查", "需要检查", "检查什么"],
        "disease_prevent": ["预防", "怎么预防", "如何预防", "防止"],
        "disease_lasttime": ["多久", "多长时间", "治疗周期", "疗程"],
        "disease_cureway": ["怎么治疗", "如何治疗", "治疗方法", "治疗方式"],
        "disease_cureprob": ["治愈率", "能治好吗", "治好的概率", "治好"],
        "disease_easyget": ["易感", "哪些人容易", "什么人容易", "高危人群"],
        "disease_desc": ["是什么", "什么意思", "介绍", "解释"],
        "check_disease": ["检查什么病", "什么病需要", "检查确诊"],
        "food_do_disease": ["什么病宜吃", "对什么病有益", "治疗什么"],
        "food_not_disease": ["什么病忌口", "什么病不能吃", "什么病少吃"],
    }


_ac_automaton = None
_ac_word_list = []


def _ensure_fallback_ready():
    """懒加载 AC 自动机组件。"""
    global _ac_automaton, _ac_word_list
    
    if _ac_automaton is not None:
        return
    
    try:
        import pyahocorasick
        from backend.domain.kbqa.config import ENTITY_DICTS
        
        _ac_word_list = []
        for etype, fpath in ENTITY_DICTS.items():
            if fpath.exists():
                with open(fpath, encoding="utf-8") as f:
                    for line in f:
                        word = line.strip()
                        if word and len(word) >= 2:
                            _ac_word_list.append((word, etype))
        
        _ac_automaton = pyahocorasick.Automaton()
        for word, etype in _ac_word_list:
            _ac_automaton.add_word(word, (word, etype))
        _ac_automaton.make_automaton()
        
        log.info("AC 自动机初始化完成，词典词条数: %d", len(_ac_word_list))
        
    except ImportError:
        log.warning("pyahocorasick 未安装，降级组件将使用朴素匹配")
        _ac_automaton = None


def _fallback_ner(question: str) -> list[dict]:
    """使用 AC 自动机或朴素匹配进行实体识别。"""
    _ensure_fallback_ready()
    
    found_entities = {}
    
    if _ac_automaton is not None:
        for end_pos, (word, etype) in _ac_automaton.iter(question):
            start_pos = end_pos - len(word) + 1
            key = (word, etype)
            if key not in found_entities:
                found_entities[key] = {
                    "name": word,
                    "type": etype,
                    "start": start_pos,
                    "end": end_pos + 1,
                }
    else:
        from backend.domain.kbqa.config import ENTITY_DICTS
        
        for etype, fpath in ENTITY_DICTS.items():
            if not fpath.exists():
                continue
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    word = line.strip()
                    if word and len(word) >= 2 and word in question:
                        key = (word, etype)
                        if key not in found_entities:
                            start_pos = question.find(word)
                            found_entities[key] = {
                                "name": word,
                                "type": etype,
                                "start": start_pos,
                                "end": start_pos + len(word),
                            }
    
    entities = sorted(found_entities.values(), key=lambda x: x["start"])
    return entities


def _fallback_full(question: str) -> tuple[list[str], list[dict], bool]:
    """完全离线分析：使用词典 NER + 关键词意图分类。"""
    entities = _fallback_ner(question)
    
    from backend.domain.kbqa.config import DENY_DICT_PATH
    
    has_negation = False
    if DENY_DICT_PATH.exists():
        with open(DENY_DICT_PATH, encoding="utf-8") as f:
            deny_words = [line.strip() for line in f if line.strip()]
            has_negation = any(word in question for word in deny_words)
    
    entity_types = {e["type"] for e in entities}
    intents = _keyword_classify(question, entity_types)
    
    return intents, entities, has_negation


def analyze_with_fallback(state: QAState) -> dict:
    """节点1：使用 LLM 分析用户问题，提取意图和实体（支持三级降级）。
    
    Level 1: 全 LLM 分析
    Level 2: LLM 实体 + 关键词意图
    Level 3: 词典 NER + 关键词意图
    """
    # 延迟初始化依赖
    _init_dependencies()
    
    question = state["question"]
    # 多轮：将历史拼入分析用问句，不修改 state["question"] 本身
    chat_history = state.get("chat_history")
    analyze_text = enrich_question_with_history(question, chat_history)
    
    # 调试日志：打印原始问题和增强后的问题，便于排查多轮对话效果
    if chat_history:
        log.info("【多轮对话】检测到历史消息 %d 条，当前原始问题: %s", len(chat_history), question)
        if analyze_text != question:
            log.info("【多轮对话】增强后的问题: %s", analyze_text)
    else:
        log.info("【单轮对话】无历史消息，原始问题: %s", question)

    # ==================== Level 1: 全 LLM 分析 ====================
    log.debug("尝试 Level 1: 全 LLM 分析")
    analysis = _llm_engine.analyze(analyze_text)
    
    if analysis and analysis.get("entities"):
        # 归一化实体
        normalized = _normalizer.normalize(
            analysis["entities"], analysis["has_negation"]
        )
        entity_dict = normalized["entity_dict"]
        entities_map = normalized["entities"]

        if entity_dict:
            intents = analysis.get("intents", [])
            if intents:
                # Level 1: 全 LLM — 意图和实体都有
                log.info("使用 Level 1: 全 LLM 模式")
                return {
                    "intent": intents,
                    "entities": analysis["entities"],
                    "params": {"has_negation": analysis["has_negation"]},
                    "analysis_level": 1,
                    "error": "",
                    "no_results": False,
                }
            else:
                # Level 2: LLM 实体 + 关键词意图
                log.warning("LLM 未返回意图，降级到 Level 2: LLM 实体 + 关键词意图")
                types = set()
                for type_list in entities_map.values():
                    types.update(type_list)
                intents = _keyword_classify(analyze_text, types)
                return {
                    "intent": intents,
                    "entities": analysis["entities"],
                    "params": {"has_negation": analysis["has_negation"]},
                    "analysis_level": 2,
                    "error": "",
                    "no_results": False,
                }

    # ==================== Level 3: 词典 NER + 关键词意图 ====================
    log.warning("LLM 分析失败或无实体，降级到 Level 3: 词典 NER + 关键词意图")
    intents, entities, has_negation = _fallback_full(analyze_text)
    
    return {
        "intent": intents,
        "entities": entities,
        "params": {"has_negation": has_negation},
        "analysis_level": 3,
        "error": "",
        "no_results": False,
    }
