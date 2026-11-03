# AI（Artificial Intelligence，人工智能）推广搜：大模型与推荐、广告、搜索的结合

## 本文其他缩写

LLM（Large Language Model，大语言模型）；CTR（Click-Through Rate，点击率）；RAG（Retrieval-Augmented Generation，检索增强生成）；ROI（Return on Investment，投资回报率）；MTGR（Meituan Generative Recommendation，美团生成式推荐）；HSTU（Hierarchical Sequential Transduction Unit，分层序列转导单元）；MTFM（Meituan Foundation Model for Recommendation，美团推荐基座模型）；BM25（Best Matching 25，经典概率相关性排序函数）；NDCG（Normalized Discounted Cumulative Gain，归一化折损累计增益）；ID（Identifier，标识符）；A/B（A/B Test，A/B 对照实验）。`@K` 表示前 K 个结果；p95/p99 表示第 95/99 百分位时延。下文沿用缩写。

这里的“推、广、搜”分别指推荐、广告、搜索。大模型可用于语义理解、内容表征、生成、重排和辅助分析；是否采用，取决于**增量价值、延迟、算力成本、可靠性与可审计性**。不能把“用了 LLM”当作业务效果。

## 1. 从传统链路切入

| 场景 | 传统核心 | AI 可能补强的环节 | 不可省略的约束 |
| --- | --- | --- | --- |
| 推荐 | 多路召回、CTR/时长/留存预估、重排 | 内容语义、多模态理解、长序列兴趣、生成式候选 | 时延、曝光偏差、多样性、长期价值 |
| 广告 | 候选、出价、pCTR/pCVR、预算节奏、归因 | 创意生成、语义匹配、用户/广告表征、复杂交互 | 预算、合规、用户体验、转化增量 |
| 搜索 | query 理解、词项/向量召回、相关性排序 | 查询改写、RAG、答案生成、语义重排 | 来源可核验、事实正确、无结果率、时延 |

## 2. 理论基础

**表示学习**把用户、query、物品和上下文映射到可比较空间；双塔利于大规模近邻召回，交叉编码器/大模型可在较少候选上做更精细的交互，但成本较高。

**序列建模**利用行为顺序和时间间隔估计动态兴趣。注意最近点击可能是短暂需求，长期行为提供稳定偏好；训练时需避免把未来行为混入特征。

**多目标学习**同时预测点击、转化、停留、投诉等，最终决策需设权重、约束或 Pareto 取舍。模型预测的转化概率与策略带来的**增量转化**不同；预算分配更应关注增量。

**生成式方法**可生成内容、搜索答案或推荐候选。生成任务必须有可验证的候选集、约束、去重、事实核查及回退机制；生成结果不能直接绕过业务规则。

**成本与效果的约束形式：**可以把决策写作 `max 预期用户价值`，同时满足 `p95时延 ≤ 阈值`、`推理成本 ≤ 预算`、`投诉/错误率 ≤ 护栏`。实际阈值由业务确定。这比只优化离线模型分数更接近在线系统问题。

## 3. 推荐中的 AI 落地

基础路线：内容图文/视频表征 → 用户历史序列 → 召回或排序特征 → 离线评估 → 灰度/A/B。模型可在召回侧改善长尾和冷启动，在精排侧建模复杂交互，在重排侧平衡多样性和长期目标。

美团公开 MTGR 在外卖首页推荐中基于 HSTU 进行序列建模，并在 2026 年公开 MTFM 跨业务统一兴趣建模。这些是具体企业公开的落地案例，适合学习“模型扩展必须同时解决系统开销”的思路。[美团 MTGR](https://tech.meituan.com/2025/05/19/Meituan-Generative-Recommendation.html)、[美团 MTFM](https://tech.meituan.com/2026/09/22/Meituan-Foundation-Model-for-Recommendation.html)

## 4. 广告中的 AI 落地

广告系统常见决策链：资格过滤 → 候选召回 → 相关性/转化预估 → 出价与预算约束 → 展示 → 归因与实验。大规模候选下，召回质量会限制后续排序上限。

Meta 公开的 Andromeda 是广告召回系统，2024 年介绍模型、索引和硬件协同，2026 年更新介绍更丰富的召回模型与大规模候选打分；这体现“模型架构与服务系统协同设计”，并非说明所有广告平台都采用相同结构。[Meta Andromeda 2024](https://engineering.fb.com/2024/12/02/production-engineering/meta-andromeda-advantage-automation-next-gen-personalized-ads-retrieval-engine/)、[Meta Andromeda 2026](https://engineering.fb.com/2026/10/28/ml-applications/meta-andromeda-next-gen-ads-retrieval-gpu-co-design/)

广告创意生成的评估要区分素材质量、点击/转化、广告主 ROI 和用户体验；避免让生成模型直接产生未经审核的承诺。可采用离线人工质量检查、小流量实验、坏例归因和持续监控。

## 5. 搜索中的 AI 落地

**RAG 简化链路：**query 理解/改写 → 权限与来源过滤 → 词项+向量检索 → 重排 → 证据选择 → 生成答案并链接来源 → 事实与安全检查 → 用户反馈。检索失败和生成失败要分开诊断。对购物搜索，还须考虑商品可售性、价格、库存、地理和转化链路。

美团搜索 3.0 公开把 LLM 语义表征用于 query 与商品的匹配，并与统计交叉特征结合，说明语义相关性和历史行为各提供不同信号。[美团搜索 3.0](https://tech.meituan.com/2026/08/20/01-meituan-Query-3.0.html)

Google 2026 年公开更新 AI 搜索的内联来源链接与官网链接展示。这是产品层面对“答案可追溯、可继续探索”的实践；仅有生成答案而无来源，很难用于高可信搜索体验。[Google Search 官方更新](https://blog.google/products-and-platforms/products/search/updates-ai-mode-overviews-explore-web/)

## 6. 评测与上线门槛

| 阶段 | 关键指标 | 典型错误 |
| --- | --- | --- |
| 离线检索 | Recall@K、相关性、无结果率、分群覆盖 | 只评估热门 query |
| 离线生成 | 事实正确、引用支持率、拒答正确率、坏例类型 | 只用一个模型当裁判，缺人工复核 |
| 服务 | p95/p99 时延、成本、超时、回退率 | 模型质量好却无法稳定在线 |
| 线上实验 | 任务成功、长期留存、转化增量、投诉与退款 | 只看 CTR 或调用量 |

**推荐的上线过程：**离线基线 → 影子流量/回放（若可用）→ 小流量灰度 → A/B → 长期护栏与复盘。每一步保留版本、数据、提示词或模型配置、实验 ID 和回退方案。

## 7. 可复现的小练习

选 100–500 条公开/自建 query-document 样本，做 BM25、向量、融合检索三路；再用小模型或 LLM 重排前 20 条，手工标注一部分相关性。报告 Recall@20、NDCG@10、时延与错例。若做 RAG，额外记录答案每个关键主张是否有检索证据支持。此练习是公开数据项目，不能写成大厂线上经验。
