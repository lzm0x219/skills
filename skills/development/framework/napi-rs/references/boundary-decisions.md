# 边界决策与回归

按入口已确定的 crate、CLI 和 Node 版本查证；以下是选择与验收问题，不固定某个版本的函数签名。

## 数值与类型契约

先确定值域、是否允许损失精度、缺省值语义和运行时输入类型，再选择转换。精确整数可能超过 JavaScript 安全整数范围时，比较 `bigint`、经验证的十进制字符串，或明确限幅的 `number`；保留已承诺的公开类型，需要变更时按兼容性处理。

不要按 Rust 位宽猜映射，也不要仅修改 `.d.ts` 来宣称运行时安全。查 [Type conversions](https://napi.rs/docs/concepts/type-conversions)：转换方向、feature 和有损窄化检查可能不同。测试安全整数边界、范围外值、负数、非整数，以及不适用的 `NaN`／无穷值；确认失败形状与声明一致。

## Buffer 与引用

对进入后台的每个值分别回答：谁维持存活，谁还能访问字节，谁负责释放。scoped 借用不能因 Rust 编译通过就被延长。持有引用的 Buffer 可以保持内存存活，但 JavaScript 仍可能修改同一份字节。

默认在仍可安全读取输入的边界复制成独立 Rust 数据；若要求 zero-copy，先给出能排除全部并发访问的协议，包括 JavaScript、其他 Rust 线程和共享内存来源。仅在 Rust 一侧加锁不约束 JavaScript 写入。无法建立协议时说明复制成本，不用 `unsafe` 隐藏缺口。见 [Understanding lifetime](https://napi.rs/docs/concepts/understanding-lifetime)。

验证输入在调用后被修改时的约定结果、值释放和 worker 退出；应检查设计避免数据竞争，不能把一次未崩溃当作内存安全证明。

## 取消、背压与退出

长任务区分排队、运行、完成、取消请求和已停止。Promise 被丢弃或客户端超时不证明原生工作停止；运行中的任务需要可检查的协作取消与资源清理。确认所用版本 `AbortSignal` 的实际边界。

跨线程回调明确队列上限和满队列策略；零上限可能表示无界，不能凭直觉解释。退出时停止接收任务、通知生产者、解除等待并释放所属环境的引用。按 [Async and concurrency](https://napi.rs/docs/more/async-concurrency) 核对取消与队列语义。

验证排队取消、运行中取消、慢消费者、重复关闭和 worker 退出；用有界超时检测挂起，并核查 Promise 结束后是否仍有后台工作。

## 最终 package

Rust 测试和从构建目录加载 `.node` 不覆盖用户安装路径。打包或 loader 改动时，使用项目包管理器的本地打包能力，检查 tarball 内容，在临时消费者中安装该本地产物并从公开入口导入。先审查会运行的 lifecycle scripts；打包不等于发布授权。

对声明支持的 ESM／CJS 入口、导出名称、生成类型和受影响错误路径分别验证。真实产物缺失的 optional platform package、跨平台 loader 或 WASI fallback 保持未验证，不以宿主机器的直接导入替代。参见 [Testing and debugging](https://napi.rs/docs/more/testing-debugging) 与 [Integrations and bundlers](https://napi.rs/docs/more/integrations)。
