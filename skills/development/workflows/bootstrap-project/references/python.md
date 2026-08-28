# Python 项目初始化适配器

此 Python 适配器适用于一个作为库或 CLI/应用的已打包 Python project。新建模式仅接受不存在或为空的目标目录；已有模式仅接受带有仓库本地 `.git` 元数据的 Git 仓库精确根目录。

## 确定版本与形态

采用标准版本优先级：用户明确选择，其次是已有 project 的精确约束，最后是执行当日从负责的官方来源验证的当前稳定版本。随包基线于 2026-08-14 验证：Python `3.14.7`、uv `0.12.4`、uv build backend `0.12.4`、build `1.5.0`、mypy `2.3.0`、pytest `9.1.1`、Ruff `0.16.3`、Lefthook `2.1.10` 和 mise `2026.8.5`；这些值仅为带日期的证据。不要选择 PyPI 已 yank 的 build `1.5.1`。

新建模式要求每个所列工具和依赖都有精确版本、有效且已规范化的 Python distribution name，以及 `library` 或 `cli`。已有模式从 PEP 621 metadata 与已识别的 `src` 布局推导名称和形态。其精确 Python 版本来自 `.python-version`，并且必须满足 `project.requires-python`；显式参数必须与已有精确 pins 一致。

## 运行适配器

在目标目录之外使用新的报告路径：

```sh
python3 <skill-directory>/scripts/bootstrap_python.py \
  --target <absolute-target> \
  --mode <new|existing> \
  --shape <library|cli> \
  --name <distribution-name> \
  --python-version <x.y.z> \
  --uv-version <x.y.z> \
  --build-version <x.y.z> \
  --mypy-version <x.y.z> \
  --pytest-version <x.y.z> \
  --ruff-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

已有模式省略 `--name`。仅当已识别 `pyproject.toml` 中已有同一精确版本时，才可省略依赖版本参数。 `--shape` 可选，但提供时必须一致。

新建模式初始化 Git 但不创建 commit，安装精确 mise 工具，调用官方 `uv init --lib` 或已打包的 `uv init --app`，验证其已知输出边界，仅替换这些生成文件为选定的最小 templates，锁定并同步精确依赖，安装 Lefthook，并运行 `mise run ci`。即使 uv 的默认 initializer 只会写入 minor version，精确 patch-level Python pin 也属于 mise 和 `.python-version`。

已有模式绝不运行 `uv init`，绝不重写 `pyproject.toml`、`uv.lock`、`.python-version`、源码、测试或 README。它仅接受 PEP 621 metadata、已识别的 uv build backend、精确 development dependency pins、Ruff、严格 mypy、pytest 配置、当前已锁定的 uv environment，以及 library 或薄 CLI 的 `src` 布局。Poetry、PDM、Pipenv、asdf、Husky、pre-commit、legacy setup files、嵌套 projects、自定义 hooks 和未知基线目标均为阻塞冲突。

## 生成的质量基线

- `install`：`uv sync --locked --all-groups`；
- `format` 和 `format-check`：Ruff format；check mode 只读；
- `lint`：禁用 cache 的 Ruff check；
- `check`：在 `src` 与 `tests` 上严格运行 mypy，并禁用其 cache；
- `test`：禁用 cache provider 的 pytest；
- `build`：通过已锁定 uv environment 运行 `python -m build --installer=uv`；
- 串行 `ci`：locked sync、format-check、lint、check、test，最后 build；
- pre-commit：`piped: true` 让部分暂存防护、暂存 Ruff formatter 及只对这些文件的显式重新暂存、全项目 Ruff lint、再到 mypy 按失败即停顺序执行。完整 pytest 和 build 不放入 hook。版本锁定的安装器验证 Lefthook 生成的 hook，加入官方 `--no-stage-fixed` 运行参数，并将 `MISE_TRUSTED_CONFIG_PATHS` 限定到该 hook 进程而不持久化全局信任；formatter helper 直接从 Git index 读取 NUL 分隔的 Python 路径；
- Ubuntu CI 通过相同的 `mise run ci` 入口、不可变 action SHA，以及对 mise、PEP 621、uv lock artifacts 和 Actions 的 Renovate 覆盖。明确禁用 lockfile maintenance。

新的 library 包含 `py.typed`。新的 CLI 将打印和参数处理置于薄的 `src/<module>/cli.py` 代码，并将经测试行为置于 `core.py`。

## 失败语义

`blocked` 表示目标、package 边界、版本、VCS、manager、hook、形态、metadata、lockfile 或目标路径冲突阻止了应用。 `partial` 表示已知写入或外部命令失败；保留报告、精确失败命令和部分变更。 `completed` 要求已安装 hook、精确 mise 与 uv lockfiles、成功的完整质量门，以及新建模式下为空的 Git history。
