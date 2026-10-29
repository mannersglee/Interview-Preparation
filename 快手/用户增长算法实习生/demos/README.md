# 用户增长补贴算法 Demo

以下项目均用固定随机种子的**合成数据**构建可运行的 Notebook，数值只用于教学，不能代表快手真实业务。每个项目包含问题定义、数据生成、建模或决策、图表分析、局限与上线验证方案。当前目录未提供匹配的真实数据，因此没有实证分析；若后续获得经过授权且脱敏的数据，可依照 Notebook 末尾的数据接口说明追加。

| 项目 | 对应 Notebook | 核心内容 |
| --- | --- | --- |
| 1. 补贴增量效果与定向投放 | [01_uplift_and_budget.ipynb](01_uplift_and_budget.ipynb) | 构造随机实验；估计异质性增量效果；比较随机、按自然活跃排序和按 uplift 排序；预算敏感性分析 |
| 2. 多档补贴出价与离线评估 | [02_bid_and_offpolicy.ipynb](02_bid_and_offpolicy.ipynb) | 生成多金额历史日志；展示选择偏差；用 IPS/DR 评估候选策略；优化预算下的金额分配 |
| 3. 在线探索与预算节奏 | [03_bandit_and_pacing.ipynb](03_bandit_and_pacing.ipynb) | 非平稳人群模拟；对比固定策略、贪心和 UCB；分析累计收益、后悔值、预算节奏与护栏 |

建议阅读顺序为 1 → 2 → 3：先明确“增量”，再学习“金额”，最后处理“在线学习”。运行环境为 `/opt/anaconda3/envs/myenv/bin/python`，依赖 NumPy、pandas、Matplotlib、scikit-learn、nbformat 和 Jupyter。运行示例：

```bash
/opt/anaconda3/envs/myenv/bin/jupyter nbconvert --execute --to notebook --inplace demos/01_uplift_and_budget.ipynb
```
