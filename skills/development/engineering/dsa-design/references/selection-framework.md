# 选择框架

在根据操作模式与约束生成候选方案时使用本参考。它只是起点，不是自动答案。

## 操作模式

| 需要                       | 优先选择                            | 仅在充分理由下考虑                        |
| -------------------------- | ----------------------------------- | ----------------------------------------- |
| 固定且小的数据的按位置访问 | Array 或 tuple                      | 预计算表或 bitset                         |
| 编译期固定键集合           | Record、struct 或 enum 索引数组     | 键集合必须动态变化时用 map                |
| 按稳定键查找               | Hash map                            | Ordered map 或数据库索引                  |
| 成员关系与唯一性           | Set                                 | 小而稠密的全集用 bitset                   |
| 后进先出处理               | Stack 或数组尾部                    | Segmented stack                           |
| 先进先出处理               | Queue 或 deque                      | 有界 ring buffer                          |
| 两端插入与删除             | Deque                               | Ring buffer                               |
| 保持插入顺序               | Array 加 map                        | Ordered map                               |
| 有序遍历或范围查询         | Sorted array 或数据库索引           | Balanced tree 或 B-tree                   |
| 重复取最小／最大值         | Heap                                | Balanced tree 或 bucket queue             |
| 高频优先级更新或取消       | Heap 加 key map                     | Indexed heap 或 balanced tree             |
| Top-K 获取                 | 大小为 K 的 heap                    | Quickselect、bucketing 或数据库聚合       |
| 前缀搜索                   | Sorted array                        | Trie 或数据库文本索引                     |
| 固定且稠密的关系           | Matrix 或预计算表                   | Bitset rows                               |
| 稀疏且动态的关系           | Adjacency list                      | 专用图索引                                |
| 依赖排序                   | DAG 加 topological sort             | 增量依赖维护                              |
| 动态连通性                 | Graph traversal                     | 边不删除时用 union-find                   |
| 最短路径                   | 单位权重用 BFS；非负权重用 Dijkstra | 保持正确性的启发式 A*；负边使用专用算法   |
| 重叠区间                   | Sorted endpoints                    | Interval tree 或 sweep line               |
| 重复纯计算                 | 直接重算                            | Memoization 或有界 cache                  |
| 重复聚合更新               | 全量重算基线                        | 增量聚合或 materialized views             |
| 小规模一次过滤             | Linear scan                         | 只有重复查询有证据时才建索引              |
| 数据大于内存               | 单遍 streaming                      | External sort、chunked merge 或数据库执行 |
| 近似成员关系               | 精确 set                            | 可接受 false positives 时用 Bloom filter  |
| 近似基数                   | 精确 set                            | 可接受误差时用 HyperLogLog                |
| 空间范围或最近邻           | Linear scan 或数据库空间索引        | R-tree、k-d tree 或 grid index            |

## 算法模式

- 固定循环域使用直接索引和模运算。
- 有限且稳定的规则映射使用查找表。
- 一次预排序能简化后续多次操作时使用排序。
- 只有顺序与单调移动保持正确性时，才使用双指针或滑动窗口。
- 只有被搜索关系有序且能保持有序时，才使用二分搜索。
- 使用图算法前，显式建模节点、边、方向、权重和更新行为。
- 只有能证明重叠子问题和可复用状态定义时，才使用动态规划。
- 只有能论证局部最优性质时，才使用贪心算法。
- cache 只用于键稳定、失效策略可接受、内存有界且复用率可信的情况。

## 非渐近检查

同时比较：常数因子与真实最大规模、内存布局／局部性／分配／GC、数据库查询数／磁盘访问／网络往返／序列化、可变性与同步成本、锁竞争／无锁结构的内存序要求／背压、持久化与序列化、cache 的键／容量／淘汰／失效／污染风险、标准库与数据库支持、确定性与遍历顺序、可观测性与可解释性，以及实现／测试／迁移成本。

## 过度工程信号

在数据固定或小、操作频率低、数据库已有所需索引、专用结构没有可测约束支撑、设计只面向模糊未来增长、数据结构泄漏到大量调用方接口，或维护不变量的成本超过其加速效果时，优先基线方案。

## 对抗输入检查

- 不只依赖哈希平均复杂度；检查运行时的冲突防护与最坏行为。
- 为用户可控的键数量、队列长度、递归深度、cache 条目和中间结果设定资源边界。
- 识别攻击者可通过输入大小、结构或分布放大的昂贵路径；没有需求或复杂度下界说明、没有输入或资源边界时，尤其避免超线性或指数工作。
- `O(n log n)` 若有明确功能需要或复杂度下界（如排序）可以合理，但仍要按最大输入、时间、内存和并发限制评估资源风险。
- 近似结构说明具体误差模式（false positives、false negatives 或估计偏差）、误差边界及攻击者可控分布的影响。
- streaming 与并发结构说明背压、丢弃、阻塞与过载策略。
