# 数据爬虫 (data_spider)

## 用途

从医药网站（jib.xywy.com 疾病百科）自动采集疾病相关数据，输出 JSONL 格式到 `backend/data/medical.json`。

采集的字段（共 18 个）：

| 字段 | 来源页面 | 说明 |
|------|---------|------|
| name, desc, category | 概述页 | 疾病名称、描述、科室分类 |
| cause, prevent | 病因/预防页 | 病因、预防措施 |
| symptom | 症状页 | 症状列表 |
| check | 检查页 | 检查项（二级解析：列表页→详情页） |
| treat (cure_way, cure_lasttime 等) | 治疗页 | 治疗方式、周期、治愈率 |
| do_eat, not_eat, recommand_eat | 食物页 | 宜吃/忌吃/推荐食谱 |
| acompany | 概述页属性 | 并发症（LLM/词典/分隔符三级降级切分） |
| yibao_status, get_prob, easy_get, get_way | 概述页属性 | 医保、患病比例、易感人群、传染方式 |
| cure_department, cost_money, cured_prob | 概述页属性 | 就诊科室、治疗费用、治愈率 |

> 注：药品数据（recommand_drug, drug_detail, common_drug）已于 2026 年被网站全站下线，爬虫保留解析逻辑但预期返回空值。

## 核心优势

### 1. 断点续爬

```bash
python main.py --resume   # 从上次中断处继续
```

- 进度保存在 `.spider_progress.json`（已完成页码集合）
- 每 50 页自动保存一次进度
- Ctrl+C 中断时立即保存进度
- 恢复时使用 append 模式，不丢失已爬数据

### 2. 三级降级并发症切分

```
Level 1: LLM（云端 API，语义理解，效果最优）
  ↓ 失败/不可用
Level 2: 词典最大双向匹配（8807 条疾病词典）
  ↓ 词典未加载
Level 3: 简单分隔符切分（、，,；; 兜底）
```

通过 `.env` 配置 Spider 专用 LLM（支持不同厂商的 OpenAI 兼容接口）：

```env
SPIDER_LLM_MODEL=deepseek-v4-pro
SPIDER_LLM_BASE_URL=https://api.ccagent.cn/v1
SPIDER_LLM_API_KEY=sk-your-key-here
```

未配置时自动回退到项目主 LLM，LLM 不可用时自动降级到词典/分隔符。

### 3. 容错机制

- **HTTP 重试**：3 次重试 + 递增等待（1s, 2s, 3s）
- **单页隔离**：某页异常不影响其他页，记录错误继续
- **404 快速跳过**：返回 404 时立即返回空，不重试
- **GBK 编码处理**：自动设置 `resp.encoding = "gbk"`
- **反爬延迟**：每次请求间隔 0.3s + 随机 0~0.3s

### 4. 多 xpath Fallback

每个解析器都有精确匹配 + 模糊匹配两层 xpath：

```python
# 精确匹配（优先）
sel.xpath('//div[@class="exact-class"]/p/text()')
# 模糊匹配（降级）
sel.xpath('//div[contains(@class,"partial-class")]//p/text()')
```

## 文件说明

| 文件 | 职责 |
|------|------|
| `main.py` | CLI 入口（argparse 参数解析） |
| `spider.py` | 爬虫主类（HTTP 请求、断点续爬、流程编排、检查项二次解析） |
| `parsers.py` | 页面解析器（8 个子页面 xpath 解析 + 数据转换 transform） |
| `config.py` | 配置（输出路径、HTTP 头、字段映射 ATTR_MAP、停用词） |
| `word_splitter.py` | 并发症分词（LLM/词典/分隔符三级降级） |

## 运行命令

```bash
cd backend/domain/data_spider

# 全量爬取（约 5-6 小时）
python main.py

# 断点续爬
python main.py --resume

# 指定范围
python main.py --start 1 --end 100

# 测试模式（打印不写文件）
python main.py --start 1 --end 5 --test

# 自定义参数
python main.py --delay 0.5 --output /path/to/output.json
```

## 输出格式

JSONL（每行一条 JSON），示例：

```json
{"name": "百日咳", "desc": "百日咳是由百日咳杆菌所致的急性呼吸道传染病...", "category": ["疾病百科", "儿科", "小儿内科"], "symptom": ["痉挛性咳嗽", "低热", "干咳"], "cure_department": ["儿科", "小儿内科"], ...}
```
