# 仓库指南

本仓库包含可移植的 Agent Skills，以及保持其元数据、文档与行为契约一致的检查工具。

## 项目结构与模块组织

- `skills/<category>/<skill-name>/` 存放每个 Skill。可移植入口放在 `SKILL.md`；任务细节放在 `references/`；确定性 helper 放在 `scripts/`；可选 Codex 元数据放在 `agents/openai.yaml`。
- `evals/<skill-name>.behavior.json` 定义源断言与行为场景；对应固定答案放在 `evals/fixtures/<skill-name>/`。
- `scripts/` 存放 Python 验证器和行为运行器；`tests/` 用标准库单元测试覆盖它们。
- `docs/` 说明评测设计；`.github/workflows/validate.yml` 记录必须的持续集成检查。

## 构建、测试与开发命令

没有构建步骤。提交改动前运行以下离线检查：

```sh
oxfmt .
oxfmt --check .
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/run_behavior_evals.py \
  --skill dsa-design --answers evals/fixtures/dsa-design
```

`oxfmt .` 使用 Oxc 格式化支持的文件；`oxfmt --check .` 在不写入时验证格式。将 `dsa-design` 换成改动的 Skill。行为命令未传 `--answers` 时会调用已认证的 Codex 服务。只在刷新官方文档覆盖率时，使用 `README.md` 记录的 Skill 专用 Node.js 清单脚本。

## 编码风格与命名

Python 使用四空格缩进、`snake_case` 函数和变量、`PascalCase` 测试类。优先使用附近代码已有的标准库和类型注解。Skill 目录使用小写 kebab-case，如 `napi-rs`，评测文件名称与其保持一致。Markdown 标题应描述明确并使用句式大小写。使用 Oxc 格式化支持文件，遵循相邻 Python 风格，并让验证器强制结构规则。

## 测试指南

测试使用 `unittest`；文件命名为 `test_*.py`，方法命名为 `test_*`。验证器或运行器行为改变时补充或更新单元测试。Skill 的可观察行为改变时更新行为契约和 fixtures。固定答案测试验证运行器，不验证当前模型质量。

## 提交与 Pull Request 指南

近期历史偏好简洁的 Conventional Commit 风格主题，包括 `docs:`、`feat:` 和 `test(validation):` 等带作用域形式。使用祈使式摘要，每次提交保持聚焦。

Pull Request 应说明受影响的 Skill 或工具、用户可见行为和已运行的验证命令；关联相关 issue，并单独说明联网或实时模型检查。只有渲染 UI 受影响时才附截图。

## Agent Skills

### Issue tracker

Issue 和规格使用本仓库 GitHub Issues 跟踪。参见 `docs/agents/issue-tracker.md`。

### Triage labels

使用五个规范 triage 标签。参见 `docs/agents/triage-labels.md`。

### Domain docs

使用单上下文领域文档布局。参见 `docs/agents/domain.md`。
