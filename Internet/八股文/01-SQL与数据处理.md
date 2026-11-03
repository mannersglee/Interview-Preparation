# SQL 与数据处理

以下 SQL 以通用语法示意；日期函数在 SQLite、MySQL、Hive 等数据库中写法不同，面试先说明所用方言。表 `events(event_id, user_id, event_time, event_type)` 和 `users(user_id, signup_date, channel)` 为示例，其中 `event_id` 是唯一事件键。

以下是本文用到的日期写法对照（假设 `event_time` 是时间戳，`signup_date` 是日期）：

| 用途 | SQLite | MySQL | Hive |
| --- | --- | --- | --- |
| 提取事件日期 | `DATE(event_time)` | `DATE(event_time)` | `TO_DATE(event_time)` |
| 注册日期加一天 | `DATE(signup_date, '+1 day')` | `DATE_ADD(signup_date, INTERVAL 1 DAY)` | `DATE_ADD(signup_date, 1)` |

因此，下面次日留存的连接条件在 MySQL 中可写为 `DATE(e.event_time) = DATE_ADD(u.signup_date, INTERVAL 1 DAY)`，在 Hive 中可写为 `TO_DATE(e.event_time) = DATE_ADD(u.signup_date, 1)`。先统一事件时间与注册日期的时区，再按天比较；若字段是字符串，还需确认其格式能被相应数据库正确解析。

## 基础高频问答

**Q：`WHERE` 和 `HAVING` 的区别？** `WHERE` 在分组前过滤行；`HAVING` 在分组后过滤聚合结果。过滤原始事件日期用 `WHERE`，筛选 DAU 大于阈值的日期用 `HAVING`。

**Q：`COUNT(*)`、`COUNT(col)`、`COUNT(DISTINCT col)`？** 分别数行、数非 NULL 值、数非 NULL 的唯一值。统计 DAU 通常是按天 `COUNT(DISTINCT user_id)`；若同一用户多条事件，`COUNT(*)` 会高估。

**Q：内连接和左连接？** 内连接只保留两边匹配行；左连接保留左表全部行，右表无匹配补 NULL。算“未下单用户”可左连接订单并判断右侧键为 NULL。连接前先确认键是否唯一，否则行数可能膨胀。

**Q：`NULL` 与 0？** NULL 表示未知或缺失，`NULL = NULL` 不为真，应用 `IS NULL`。算比例时用 `NULLIF(denominator,0)` 避免除零；缺失不能随意当作 0。

**Q：窗口函数和 `GROUP BY`？** `GROUP BY` 折叠为每组一行；窗口函数保留原行并附加分组统计、排名或前后值。常用 `ROW_NUMBER()` 去重，`LAG()` 看上期值。

## 必会题型与参考写法

**1. 每日活跃用户数。** 明确活跃事件口径和时区；示例把任一事件视为活跃。

```sql
SELECT DATE(event_time) AS dt, COUNT(DISTINCT user_id) AS dau
FROM events
WHERE event_time >= '2026-10-01' AND event_time < '2026-11-01'
GROUP BY DATE(event_time);
```

**2. 每个用户每天最后一条事件。** `ROW_NUMBER()` 需加稳定的并列排序键；若没有事件 ID，同一时间戳可能无法唯一确定。

```sql
WITH ranked AS (
  SELECT e.*, ROW_NUMBER() OVER (
    PARTITION BY user_id, DATE(event_time)
    ORDER BY event_time DESC, event_id DESC
  ) AS rn
  FROM events e
)
SELECT * FROM ranked WHERE rn = 1;
```

**3. 次日留存。** 注册用户是分母；次日是否活跃按用户去重。若 `signup_date` 为日期型，下例是 SQLite 语法。

```sql
WITH cohorts AS (
  SELECT signup_date, COUNT(DISTINCT user_id) AS new_users FROM users GROUP BY signup_date
), returned AS (
  SELECT u.signup_date, COUNT(DISTINCT u.user_id) AS retained
  FROM users u JOIN events e ON u.user_id = e.user_id
   AND DATE(e.event_time) = DATE(u.signup_date, '+1 day')
  GROUP BY u.signup_date
)
SELECT c.signup_date, c.new_users, COALESCE(r.retained, 0) AS retained,
       1.0 * COALESCE(r.retained, 0) / NULLIF(c.new_users, 0) AS d1_retention
FROM cohorts c LEFT JOIN returned r ON c.signup_date = r.signup_date;
```

**4. 漏斗。** 先确认是同一用户在时间窗内按顺序完成曝光→点击→下单，还是仅统计各环节人数。不能只比较三类事件去重人数就称为顺序漏斗。需要用事件时间和用户 ID 校验先后，限定同一场景或商品。

## 互联网场景操作手册

拿到活跃、留存或转化需求，按以下顺序落地。以下查询采用 SQLite 日期语法；换用 MySQL 或 Hive 时，按开头的对照表替换日期函数。

1. **写清业务口径**：明确用户群、统计时区、观察窗口、有效事件、去重单位和分组维度。例如“10 月每日登录用户数”需要确认游客是否计入、登录事件是否去重；“下单转化”需要确认按用户、会话还是订单计数。
2. **确认数据粒度与键**：核对 `events` 是否一行一事件、`event_id` 是否唯一、`users` 是否一行一用户。多端登录、埋点重试可能产生重复事件；渠道归因应取注册时渠道还是事件时渠道，也要先确定。
3. **先验数再计算**：检查时间范围、空用户 ID、重复事件、事件类型分布和日志延迟。生产表若按天分区，查询时还应加分区过滤；仅按事件时间过滤可能仍扫描大量分区。

```sql
SELECT COUNT(*) AS rows_total,
       COUNT(DISTINCT event_id) AS unique_events,
       SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) AS null_users,
       MIN(event_time) AS first_event, MAX(event_time) AS last_event
FROM events
WHERE event_time >= '2026-10-01' AND event_time < '2026-11-01';
```

4. **固定分母后计算**：活跃以“日期 × 用户”去重；留存以注册 cohort 为分母；漏斗先固定起点人群，再数其中完成后续步骤的人。先把每一步的人数单独查出，再计算比率，避免连接放大。
5. **核验并交付**：检查 `留存人数 ≤ 新增人数`、`后续步骤人数 ≤ 起点人数`、分组汇总与总体是否符合去重规则。分组用户可能重叠，分组人数之和不一定等于总体去重人数。交付时附 SQL 方言、口径、时间范围、数据延迟与异常处理。

### 场景一：按渠道计算次日留存

以注册日和注册渠道划分 cohort，同一用户次日有至少一条有效事件即视为留存。先从事件表按“日期 × 用户”去重，再左连接注册用户，保证没有回访的 cohort 也能展示。此例沿用前文“任一事件算活跃”的假设。

```sql
WITH active_days AS (
  SELECT DISTINCT user_id, DATE(event_time) AS active_date
  FROM events
  WHERE user_id IS NOT NULL
), cohorts AS (
  SELECT signup_date, channel, COUNT(DISTINCT user_id) AS new_users
  FROM users
  GROUP BY signup_date, channel
), retained AS (
  SELECT u.signup_date, u.channel, COUNT(DISTINCT u.user_id) AS users_retained
  FROM users u
  JOIN active_days a ON a.user_id = u.user_id
                    AND a.active_date = DATE(u.signup_date, '+1 day')
  GROUP BY u.signup_date, u.channel
)
SELECT c.signup_date, c.channel, c.new_users,
       COALESCE(r.users_retained, 0) AS users_retained,
       1.0 * COALESCE(r.users_retained, 0) / NULLIF(c.new_users, 0) AS d1_retention
FROM cohorts c
LEFT JOIN retained r ON r.signup_date = c.signup_date
                    AND (r.channel = c.channel OR (r.channel IS NULL AND c.channel IS NULL));
```

实际跑数时，应给注册日和事件时间加所需范围，并确认最后一个注册日的次日日志已到齐。若 `users` 是用户属性变更历史表，须先按用户选定注册时的渠道记录。

### 场景二：曝光到点击的顺序转化

以用户级“首次曝光后发生点击”为例。统计窗口内的首次曝光是分母；同一用户在首次曝光之后、窗口结束之前有点击才计入分子。真实推荐或电商场景还应通过 `request_id`、商品 ID 或会话 ID 限定同一次链路，否则其他商品的点击会被误计。若需要点击到下单，再用相同的链路键和时间顺序扩展下一步。

```sql
WITH first_exposure AS (
  SELECT user_id, MIN(event_time) AS exposure_time
  FROM events
  WHERE event_type = 'exposure'
    AND user_id IS NOT NULL
    AND event_time >= '2026-10-01' AND event_time < '2026-11-01'
  GROUP BY user_id
), clicked AS (
  SELECT f.user_id
  FROM first_exposure f
  JOIN events e ON e.user_id = f.user_id
               AND e.event_type = 'click'
               AND e.event_time > f.exposure_time
               AND e.event_time < '2026-11-01'
  GROUP BY f.user_id
)
SELECT COUNT(*) AS exposed_users,
       COUNT(c.user_id) AS clicked_users,
       1.0 * COUNT(c.user_id) / NULLIF(COUNT(*), 0) AS exposure_to_click_rate
FROM first_exposure f
LEFT JOIN clicked c ON c.user_id = f.user_id;
```

这里算的是**用户级转化率**，不是按曝光次数计算的 CTR；若业务问的是 CTR，应以有效点击次数 / 有效曝光次数为口径，并处理重复埋点与曝光点击关联。

## 易错追问

- **JOIN 后指标翻倍？** 查每张表的粒度及连接键唯一性；先各自聚合到同一粒度再连接，或按业务键去重。
- **留存率可能大于 100%？** 分子与分母 cohort 不一致、重复用户、日期时区错、跨设备 ID 合并错。
- **窗口边界？** 推荐半开区间 `[start, end)`，避免月底/小时边界重叠。
- **性能题？** 先缩小扫描范围和列，按分区字段过滤；避免不必要的 `DISTINCT` 和大表多对多连接；执行计划与索引/分区要结合实际引擎解释。

## 自测清单

不用看答案，写出：DAU、按渠道次日留存、每用户最新事件、7 日滚动活跃、曝光→点击→下单漏斗。每题写明表粒度、去重键、时间窗、NULL 处理。
