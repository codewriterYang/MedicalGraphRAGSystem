#!/usr/bin/env python3
# coding: utf-8
"""
data_spider 模块单元测试

测试内容：
1. parse_drug() 适配新网站结构（药品模块已下线）
2. parse_drug() 兼容旧结构（向后兼容）
3. ATTR_MAP 已移除 common_drug 映射
4. parse_basic_info() 在缺少"常用药品"时正常工作
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# data_spider 模块内部使用相对导入（from config import ...），需要将其目录加入 sys.path
_SPIDER_DIR = str(Path(__file__).resolve().parent.parent.parent / "domain" / "data_spider")
if _SPIDER_DIR not in sys.path:
    sys.path.insert(0, _SPIDER_DIR)

from backend.domain.data_spider.parsers import PageParsers
from backend.domain.data_spider.config import ATTR_MAP, SPLIT_FIELDS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# 当前网站药品页 HTML（"暂无药品"）
DRUG_PAGE_NEW_NO_DRUG = """
<html><head><title>百日咳的药品,百日咳的用药-儿科-小儿内科-寻医问药-xywy.com</title></head>
<body>
<div class="wrap mt10 clearfix graydeep">
  <div class="good-drug-box bor">
    <div class="panels">
      <div class="city-item">
        <div class="city-drug clearfix fb bor-bot pb5" id="zzk_show">
          <span class="dib fl f15 fYaHei city-drug-name">药品</span>
        </div>
        暂无药品
      </div>
    </div>
  </div>
</div>
</body></html>
"""

# 旧版网站药品页 HTML（有药品数据）
DRUG_PAGE_OLD_WITH_DRUG = """
<html><head><title>高血压的药品-寻医问药</title></head>
<body>
<div class="fl drug-pic-rec mr30">
  <p><a>硝苯地平控释片(拜新同)</a></p>
  <p><a>缬沙坦胶囊(代文)</a></p>
  <p><a>氨氯地平片(络活喜)</a></p>
</div>
</body></html>
"""

# 概述页 HTML（无"常用药品"属性）
BASIC_INFO_NO_COMMON_DRUG = """
<html><head><title>糖尿病的简介,什么是糖尿病-内科-内分泌科-寻医问药-xywy.com</title></head>
<body>
<div class="wrap mt10 nav-bar">
  <a>疾病百科</a><a>内科</a><a>内分泌科</a><a>糖尿病</a>
</div>
<div class="jib-articl-con jib-lh-articl">
  <p>糖尿病是一种以高血糖为特征的代谢性疾病。</p>
</div>
<div class="mt20 articl-know">
  <p>医保疾病：否</p>
  <p>患病比例：8.3%</p>
  <p>易感人群：肥胖人群</p>
  <p>就诊科室：内科 内分泌科</p>
</div>
</body></html>
"""


# ---------------------------------------------------------------------------
# Task 1.1.1: parse_drug() 适配新结构
# ---------------------------------------------------------------------------

class TestParseDrugNewStructure:
    """测试 parse_drug() 适配网站药品模块下线后的新结构。"""

    def setup_method(self):
        self.parsers = PageParsers()

    def test_no_drug_returns_empty_lists(self):
        """当前网站药品页显示'暂无药品'时，应返回 ([], [])。"""
        recommand_drug, drug_detail = self.parsers.parse_drug(DRUG_PAGE_NEW_NO_DRUG)
        assert recommand_drug == []
        assert drug_detail == []

    def test_empty_html_returns_empty_lists(self):
        """空 HTML 输入应返回 ([], [])。"""
        recommand_drug, drug_detail = self.parsers.parse_drug("")
        assert recommand_drug == []
        assert drug_detail == []

    def test_none_html_returns_empty_lists(self):
        """None 输入应返回 ([], [])。"""
        recommand_drug, drug_detail = self.parsers.parse_drug(None)
        assert recommand_drug == []
        assert drug_detail == []


class TestParseDrugBackwardCompat:
    """测试 parse_drug() 兼容旧版 HTML 结构（向后兼容）。"""

    def setup_method(self):
        self.parsers = PageParsers()

    def test_old_structure_still_parses(self):
        """旧版 drug-pic-rec 结构仍能正确解析药品数据。"""
        recommand_drug, drug_detail = self.parsers.parse_drug(DRUG_PAGE_OLD_WITH_DRUG)
        assert len(drug_detail) == 3
        assert "硝苯地平控释片(拜新同)" in drug_detail
        assert "缬沙坦胶囊(代文)" in drug_detail
        assert "氨氯地平片(络活喜)" in drug_detail
        # recommand_drug 是去重后的药品通用名
        assert len(recommand_drug) >= 1


# ---------------------------------------------------------------------------
# Task 1.1.2: ATTR_MAP 清理 common_drug
# ---------------------------------------------------------------------------

class TestAttrMapCleanup:
    """测试 ATTR_MAP 已移除 common_drug 相关映射。"""

    def test_common_drug_not_in_attr_map(self):
        """ATTR_MAP 不再包含'常用药品'映射。"""
        assert "常用药品" not in ATTR_MAP

    def test_common_drug_not_in_split_fields(self):
        """SPLIT_FIELDS 不再包含 common_drug。"""
        assert "common_drug" not in SPLIT_FIELDS


# ---------------------------------------------------------------------------
# parse_basic_info() 兼容性
# ---------------------------------------------------------------------------

class TestParseBasicInfoCompat:
    """测试 parse_basic_info() 在缺少'常用药品'属性时正常工作。"""

    def setup_method(self):
        self.parsers = PageParsers()

    def test_basic_info_without_common_drug(self):
        """概述页无'常用药品'字段时，正常解析其他属性。"""
        name, category, desc, attrs = self.parsers.parse_basic_info(BASIC_INFO_NO_COMMON_DRUG)
        assert name == "糖尿病"
        assert "内分泌科" in category or "内科" in category
        assert "高血糖" in desc
        assert attrs.get("yibao_status") == "否"
        assert attrs.get("get_prob") == "8.3%"
        assert "common_drug" not in attrs
