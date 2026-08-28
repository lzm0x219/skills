# 验证与报告

仅在选定适配器已返回或跳过 apply 后阅读本参考。以选定技术栈参考为技术栈特定完成门的来源。

## 解读状态

- `blocked`：冲突阻止 apply；报告未解决决策并确认是否运行过外部命令。
- `planned`：用户只请求规划，或已确定的形态没有随包适配器。
- `partial`：写入已经开始，但 initializer、install、lock、hook 或 quality command 失败；保留目标和精确失败命令。
- `completed`：选定适配器、已安装 hook、技术栈完成门和 `mise run ci` 全部通过。

## 检查公共证据

根据目标核验适配器报告，而不是只信任其状态：

- 精确的受管版本和 lockfiles 与已识别的 project constraints 一致；
- 公共 mise tasks 与串行 `ci` 入口存在，并执行真实命令；
- Lefthook 安装有序的部分暂存防护、暂存 formatter 及重新暂存、lint 和快速 check，而不含完整 test 或 build；
- Ubuntu workflow 使用不可变 action SHA，并且仅调用一次 `mise run ci`；
- `.github/renovate.json` 扩展 recommended preset，没有 automerge，并明确禁用 lockfile maintenance；
- 新建模式不创建 Git commit；已有模式保留选定参考承诺保留的每个文件；
- caches 与 build artifacts 保持未跟踪，而预期副作用被准确报告。

在 `partial` 时，保留证据、报告恢复步骤，并将清理留给用户。在 `blocked` 时，区分 inspection 和 execution。失败或未运行的质量门不能产生 `completed`。

## 返回结果

```text
状态：completed | partial | planned | blocked
目标：<absolute path>
模式：new | existing
技术栈：Zig | Rust | TypeScript/Node.js | Python | Go | unresolved
形态：library | CLI/application | unresolved
版本：<value, precedence branch, evidence>

变更：
- 创建：<paths, or none>
- 修改：<paths, or none>
- 保留：<paths, or none>

冲突：
- <decision needed, or none>

验证：
- <command> — <passed|failed|not run>

失败命令：
- <exact argv, or none>

下一步：
- <recovery command, adapter boundary, or none>
```

只有在每个字段均得到适配器报告、目标检查或明确的 `not run` 支持时，才可完成。
