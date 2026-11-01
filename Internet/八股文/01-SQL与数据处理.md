# SQL 与数据处理

以下 SQL 以通用语法示意；日期函数在 SQLite、MySQL、Hive 等数据库中写法不同，面试先说明所用方言。表 `events(event_id, user_id, event_time, event_type)` 和 `users(user_id, signup_date, channel)` 为示例，其中 `event_id` 是唯一事件键。

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

## 易错追问

- **JOIN 后指标翻倍？** 查每张表的粒度及连接键唯一性；先各自聚合到同一粒度再连接，或按业务键去重。
- **留存率可能大于 100%？** 分子与分母 cohort 不一致、重复用户、日期时区错、跨设备 ID 合并错。
- **窗口边界？** 推荐半开区间 `[start, end)`，避免月底/小时边界重叠。
- **性能题？** 先缩小扫描范围和列，按分区字段过滤；避免不必要的 `DISTINCT` 和大表多对多连接；执行计划与索引/分区要结合实际引擎解释。

## 自测清单

不用看答案，写出：DAU、按渠道次日留存、每用户最新事件、7 日滚动活跃、曝光→点击→下单漏斗。每题写明表粒度、去重键、时间窗、NULL 处理。
