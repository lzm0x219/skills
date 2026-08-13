# Zig 与 C 互操作边界

先沿用 `SKILL.md` 确定的目标 Zig 版本；用户与仓库均未提供版本时，实时查询 Zig 官网并采用当前最新稳定版。`@cImport`、`zig translate-c`、Build API、C ABI 与链接参数均按该目标版本核对。

## 选择绑定方式

- 需要直接使用 header，并能在编译时提供一致的 include path 与 macro 环境时，优先评估 `@cImport`。
- 需要检查翻译结果、传入独立 `cflags`、修正无法自动翻译的声明或维护显式 Zig 绑定时，评估目标版本的 `zig translate-c` 工作流。
- 把生成或翻译的绑定视为边界层；业务逻辑通过手写的窄 Zig adapter 使用它，避免让 C 表示渗透整个代码库。
- 记录 header、library、target、ABI、macro、include path 和生成命令；其中任一变化都需要重新验证绑定。

## 建模 ABI 与数据

- 对跨边界类型核对 calling convention、整数宽度与符号、alignment、`extern` layout、enum、bitfield、sentinel、可空 pointer 和字符串终止规则。
- 不手工假设 C `long`、`size_t`、enum 或 struct 在不同 target 上具有相同布局。
- 需要稳定磁盘或网络格式时定义显式序列化，不把本机 C/Zig 内存布局直接当作协议。
- 在窄 adapter 中把 C 表示转换为有语义的 Zig 类型，并在同一位置转换错误与所有权。

## 明确所有权、生命周期与 callback

- 对每个 pointer、buffer、handle 和字符串写明分配者、释放函数、可变性、长度、终止方式和有效期。
- Zig 分配的内存只有在 allocator/ABI 契约允许时才交给 C；C 返回的资源只用其指定的释放函数释放。
- callback 必须明确 userdata 的 owner、注册/注销顺序、线程、重入规则和最长生命周期；不得让 callback 保留已失效的栈地址或借用 slice。
- 跨线程 callback 只传递满足线程安全与生命周期要求的数据；把 C 状态码、null、`errno` 或库特定错误转换成稳定的 Zig 错误边界。

## 配置构建与链接

- 通过目标版本的 Build API 配置 include path、C source、macro、libc、系统库、静态/动态链接和运行时搜索路径。
- 让 target 与 optimization 选项贯穿 Zig artifact、C 编译和链接步骤，避免混用不兼容 ABI 或运行时。
- 使用系统库时记录最低版本和发现机制；使用 vendored C source 时记录编译参数与许可证。

## 验证边界

1. 编译最小 header/import 或 translated binding。
2. 链接真实或受控测试 library，验证符号和 ABI。
3. 在兼容 target 环境运行 smoke test，覆盖一次成功调用和一次失败转换。
4. 对拥有资源的 API 覆盖分配、释放、部分失败和重复调用边界。
5. 对 callback 覆盖注册、触发、注销、失败和线程/重入约束。

只编译或只链接不能证明运行时 ABI 正确。报告中分别记录编译、链接、执行和未覆盖 target。

语法与工具参数以目标版本语言参考中的 [C 互操作章节](https://ziglang.org/documentation/)及 `zig translate-c --help` 为准。
