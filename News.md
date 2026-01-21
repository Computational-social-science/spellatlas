# 研究方案（Research Plan）

## 项目标题
**Global Spelling Error Fingerprints in English News (2016–Present)**  
**基于全球英文新闻的人类拼写错误行为指纹研究**

目标期刊：*Nature Human Behaviour*

---

## 1. 研究背景与科学问题

### 1.1 背景
拼写错误（spelling errors）是人类语言生产中一种**低意识、非刻意**的行为痕迹，长期以来被视为“噪声”而非研究对象。然而在大规模真实世界文本中，拼写错误并非随机分布，而是受到：

- 语言背景（母语迁移）
- 输入技术与编辑制度
- 社会—技术系统演化

等因素的系统性约束。

### 1.2 核心科学问题（NHB 导向）

> 在真实新闻生产系统中，**拼写错误的统计结构是否构成稳定、可比较、可演化的人类行为指纹？**

具体问题：
1. 不同国家的英文新闻是否呈现**稳定差异化的拼写错误结构**？
2. 这些结构在 2016–至今是否随时间发生**非随机演化**？
3. 拼写错误分布是否反映语言—文化分组的**涌现结构**？

---

## 2. 方法论立场（Methodological Positioning）

### 2.1 研究类型
- 大规模观察性研究（large-scale observational study）
- 非实验、非作者归因
- 行为痕迹分析（behavioural traces）

### 2.2 关键声明（将写入 Methods）

- 不区分 OCR / AI / 人类作者
- 将技术变化视为**时间轴上的内生演化**
- 拼写错误被建模为**新闻生产系统的涌现属性**

---

## 3. 数据设计

### 3.1 数据来源

**核心聚合源**：GDELT Project  
- 覆盖国家/地区：195+
- 时间跨度：2016–至今
- 更新频率：15 分钟
- 语言筛选：英文

**使用方式**：
- 使用 GDELT 提供的 URL、时间、国家元数据
- 二次抓取原始新闻正文

### 3.2 数据约束

| 维度 | 约束 |
|----|----|
| 时间 | 可解析发布时间（UTC） |
| 地域 | 国家级（ISO-3166） |
| 连续性 | 每日更新 |
| 文本 | 原始英文正文 |

---

## 4. 拼写错误指纹（SEF）的操作化定义

### 4.1 基本单位

- 文本集合：\( D^{(c,t)} \)
- 国家：\( c \)
- 时间窗口（年/季度）：\( t \)

### 4.2 指纹向量

\[\
\mathbf{SEF}(c,t) = [\mathbf{E}^{type}, \mathbf{E}^{char}, \mathbf{E}^{phon}, \mathbf{E}^{pos}]\
\]

#### 子空间说明（简述）
- **E^type**：编辑操作分布（插入/删除/替换/转置）
- **E^char**：字符级混淆模式（低维嵌入）
- **E^phon**：语音等价与迁移特征
- **E^pos**：词性条件错误分布

---

## 5. 技术实现方案（Python + Svelte 混合编程）

### 5.1 总体架构

```
[ GDELT API ]
      ↓
[ Python 数据管道 ] —— 数据清洗 / 拼写检测 / 向量化
      ↓
[ PostgreSQL / DuckDB ] —— 结构化存储
      ↓
[ Python 分析层 ] —— 统计 / 距离 / 时间模型
      ↓
[ API (FastAPI) ]
      ↓
[ Svelte 前端 ] —— 交互式可视化
```

---

### 5.2 Python 后端（核心研究引擎）

**主要职责**：
- 新闻抓取与解析
- 拼写错误检测
- SEF 向量计算
- 统计分析

**推荐技术栈**：
- Python 3.11+
- requests / aiohttp
- spaCy（POS, NER）
- wordfreq / wordlists
- rapidfuzz（编辑距离）
- pandas / numpy
- scikit-learn
- ruptures（时间断点）
- FastAPI（服务接口）

---

### 5.3 Svelte 前端（分析与展示）

**目的**：
- 探索性分析（EDA）
- 国家 × 时间指纹可视化
- 支持审稿与复现

**推荐技术栈**：
- Svelte + Vite
- TypeScript
- D3.js / Observable Plot
- MapLibre / GeoJSON

**核心页面**：
1. 全球 SEF 地图
2. 国家指纹雷达图
3. 时间漂移曲线
4. 国家聚类投影（PCA / UMAP）

---

## 6. 统计分析计划（NHB 风格）

### 6.1 指纹稳定性
- 国家内相似度 vs 国家间相似度
- 置换检验

### 6.2 时间演化
- 年度 SEF 距离变化
- 变点检测（无先验年份）

### 6.3 涌现结构
- 指纹空间聚类
- 与语言家族的相关性（非监督）

---

## 7. 可复现性与伦理

- 所有代码版本化（Git）
- 数据处理流水线可审计
- 使用公开新闻数据，无个人隐私

---

## 8. 项目阶段划分

| 阶段 | 内容 |
|----|----|
| Phase 1 | 数据管道与拼写检测 |
| Phase 2 | SEF 向量构建 |
| Phase 3 | 国家级分析 |
| Phase 4 | 前端可视化 |
| Phase 5 | 论文与补充材料 |

---

## 9. 预期成果

- 一套可复现的拼写错误指纹方法
- 全球国家级行为差异图谱
- 面向 *Nature Human Behaviour* 的完整论文

---

## 10. 附注（投稿级表述）

> This study treats spelling errors as emergent behavioural traces of national news production systems rather than artifacts of individual authorship.

---

## 11. Engineering Task Breakdown（开发任务拆解）

以下任务列表可直接转化为 **GitHub Issues / JIRA Tickets**，按研究优先级与工程依赖顺序排列。

---

### Phase 1 — 项目初始化与基础设施（Week 1）

**T1.1 仓库初始化**
- 建立 monorepo：`/backend`（Python）+ `/frontend`（Svelte）
- 配置 Git、README、LICENSE
- 设置 `.editorconfig`、`.gitignore`

**T1.2 Python 开发环境**
- Python 3.11+
- poetry / uv / pip-tools 任选
- 依赖分组：core / nlp / analysis / api

**T1.3 前端开发环境**
- Vite + Svelte + TypeScript
- ESLint + Prettier

---

### Phase 2 — 数据获取与原始文本层（Week 1–2）

**T2.1 GDELT 数据接入**
- 实现 GDELT 2.1 Events / Mentions 拉取
- 仅保留英文新闻
- 解析字段：URL / 时间 / 国家代码

**T2.2 原始新闻正文抓取**
- HTTP 抓取（含重试、超时）
- Boilerplate removal（正文提取）
- HTML → clean text

**T2.3 文本质量过滤**
- 去除短文本（< N tokens）
- 去重（hash + similarity）
- 排除模板化内容（财经/体育快讯）

---

### Phase 3 — 拼写错误检测模块（核心）（Week 2–3）

**T3.1 标准词表构建**
- US / UK English 词典
- 词频阈值过滤
- 专有名词白名单（NER + Gazetteer）

**T3.2 Tokenization 与 POS 标注**
- spaCy EN pipeline
- 句级与词级索引

**T3.3 拼写错误判定逻辑**
- 非词典词识别
- 编辑距离 ≤ k 的可纠正词
- 排除新词、缩写、URL、数字

**T3.4 错误—修正对生成**
- 保存 (error, correction, context)
- 为后续 SEF 向量服务

---

### Phase 4 — SEF 向量构建（Week 3–4）

**T4.1 Edit-type 统计**
- ins / del / sub / trans 计数
- 国家 × 时间归一化

**T4.2 字符级混淆矩阵**
- 统计字符替换概率
- PCA / SVD 降维

**T4.3 语音迁移特征**
- Double Metaphone / IPA 映射
- 元音 / 辅音混淆比例

**T4.4 POS 条件错误分布**
- 按词性统计错误概率

**T4.5 SEF 聚合接口**
- 输出 `SEF(c, t)` 标准向量

---

### Phase 5 — 数据存储与 API（Week 4）

**T5.1 数据库设计**
- 原始文本表
- 错误实例表
- SEF 向量表

**T5.2 FastAPI 服务**
- 查询国家 × 时间 SEF
- 提供前端消费接口

---

### Phase 6 — 统计分析（Week 5）

**T6.1 指纹距离度量**
- cosine / euclidean / mahalanobis

**T6.2 国家稳定性检验**
- within vs between similarity
- permutation test

**T6.3 时间演化分析**
- 年度漂移曲线
- 变点检测（ruptures）

---

### Phase 7 — 前端可视化（Week 5–6）

**T7.1 国家指纹雷达图**
- 多子空间可切换

**T7.2 时间漂移折线图**
- 国家对比

**T7.3 全球指纹地图**
- Map + embedding 投影

---

### Phase 8 — 论文与复现（Week 6+）

**T8.1 Methods 文档化**
- 数据
- 指纹定义
- 统计方法

**T8.2 Supplementary Materials**
- 额外分析
- 鲁棒性检验

---


> This study treats spelling errors as emergent behavioural traces of national news production systems rather than artifacts of individual authorship.

---

**文档格式**：Markdown（MD）  
**可直接用于版本控制、下载与投稿准备**

