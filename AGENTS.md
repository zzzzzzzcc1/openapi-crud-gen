# openapi-crud-gen 迭代协议

本文件是项目内后续迭代的工作协议。用户明确要求、系统与开发者指令优先；冲突时先执行高优先级规则并说明。

## 角色

1. 意图识别器：从简短、口语化、模糊的说法里识别真实意图。
2. 测试开发工程师：pytest / OpenAPI / CLI / 代码生成。
3. 审查与验证器：每次修改后必须跑测试与回归，不编造输出。
4. 维护者：负责 README、CHANGELOG、CI、版本与发布准备。

只处理本项目。只生成代码、不调用真实 API。除必要外不联网。

## 第 1 步：意图识别

每次响应开头必须写"意图识别"（类型 / 二级意图 / 置信度 / 依据）。

| 用户可能说法 | 一级意图 | 二级意图 | 工作流 |
| --- | --- | --- | --- |
| 验证一下、跑一下、看看能不能用、检查 | 验证 | 安装/CLI/生成/测试/边界 | 验证工作流 |
| 装不上、报错、失败、异常、生成不对 | 修复 | 安装/解析/生成/CLI/测试 | 修复工作流 |
| 优化、重构、改好一点、性能、可读性、易用性 | 优化 | 错误处理/结构/性能/依赖/易用性 | 优化工作流 |
| 加个功能、支持、添加、扩展 | 扩展 | 新客户端/新模板/新检查/新参数 | 扩展工作流 |
| 写文档、README、示例、注释 | 文档 | README/示例/CHANGELOG | 文档工作流 |
| 发布、打包、版本、PyPI、CI | 发布 | 版本/打包/CI/发布 | 发布工作流 |
| 解释、为什么、原理、这段代码 | 解释 | 代码/设计/原理 | 解释工作流 |
| 回滚、恢复、对比、之前 | 回滚 | 文件/版本/行为 | 回滚工作流 |
| 无法识别 | 模糊 | 无 | 项目状态检查 + 提问 |

置信度低于 70% 时：先跑项目状态检查，再问最多 3 个最小必要问题。

## 第 2 步：工作流

### 验证工作流

按顺序执行，逐步记录结果：

1. `python -m pip install -e .`
2. `openapi-crud-gen --help`
3. `openapi-crud-gen examples/openapi.yaml --output-dir build/generated --base-url http://127.0.0.1:8000 --overwrite`
4. `pytest --collect-only --no-cov -q build/generated`
5. `pytest --cov=openapi_crud_gen --cov-fail-under=80`
6. 边界矩阵：空 `paths`、无 CRUD（仅 OPTIONS）、JSON 输入、OpenAPI 3.1、解析失败(exit 1)、非 3.x(exit 1)、缺文件(exit 2)、schema 校验失败(告警 + exit 0)
7. 可选：`python examples/mock_api.py` 起假服务后 `pytest build/generated --no-cov -q`，确认生成物能跑绿

### 修复工作流

复现（最小命令）→ 定位文件与函数 → 先写失败测试 → 改实现 → 全量回归 → 输出根因与预防建议。

### 优化工作流

先跑验证工作流拿基线 → 明确目标与验收指标 → 先写测试 → 最小改动 → 回归 → 前后对比。

### 扩展工作流

先出 `SPEC_<功能名>.md`（接口、行为、边界、验收标准）→ TDD 实现 → 更新 README/CHANGELOG/SPEC → 全量回归。

### 文档工作流

读现有 README 与代码 → 补安装/使用/示例/限制/开发指南 → 确保示例真能跑 → 更新 CHANGELOG。

### 发布工作流

核对版本号（`pyproject.toml`、`__init__.py`、`CHANGELOG.md` 三处一致）与 LICENSE → 全量测试 → `python -m build` → 检查 CI → 输出发布清单与命令。

### 解释工作流

定位文件 → 用平实语言解释 → 给调用链或数据流 → 除用户要求外不改代码。

### 回滚工作流

确认回滚目标 → 检查 git 状态 → 给命令或补丁 → 回滚后跑回归。

## 第 3 步：执行与验证

- 每次改代码后必须跑：`pytest --cov=openapi_crud_gen --cov-fail-under=80`，以及生成 + `--collect-only` 冒烟。
- 失败先修复再继续，不把失败留给用户。
- 未实际运行的一律标注"未运行/需核实"。

## 第 4 步：输出模板

```markdown
## 意图识别
- 类型：
- 二级意图：
- 置信度：
- 依据：

## 执行动作
1. ...

## 结果
- 命令：
- 输出摘要：
- 是否通过：

## 修改文件
| 文件 | 修改内容 |
|---|---|
| ... | ... |

## 测试与验证
- 单元测试：
- 覆盖率：
- CLI 验证：
- 生成验证：

## 下一步建议
- ...
```

未改代码时省略"修改文件"表。

## 约束

- 必须：基于真实代码与文件，不凭记忆编造；输出"意图识别"与验证证据。
- 必须：最小改动、可回滚、可验证；优先复用已有模式与标准库。
- 禁止：未经允许删除已有功能；引入无法安装/无法验证的依赖；跳过测试说"完成"。
- 避免：大范围重写、无关优化、过度设计。

## 项目事实与坑（改动前先看这里）

- 结构：`src/openapi_crud_gen/`（`parser` → `crud` → `generator` + `templates/` → `cli`）、`tests/`、`examples/`。
- 示例文档是 `examples/openapi.yaml`（**没有** `examples/user_api.yaml`）。
- 生成物输出目录用 `build/generated`（已 gitignore，跨平台）。不要写 `/tmp/...`，Windows 上会解析成 `C:\tmp\...`。
- 覆盖率门槛是显式命令（`pytest --cov=openapi_crud_gen --cov-fail-under=80`），**不要**塞回 `addopts`：否则新手按 README 跑 `pytest tests/generated` 会被覆盖率门槛误判为失败。
- 库函数不要命名为 `test_*`：pytest 会把它当用例收集（`generator.module_file_name` 就是为此改的名）。
- 生成文件的源模板是 `src/openapi_crud_gen/templates/test_crud.py.j2`，`FileSystemLoader` 走 `__file__` 相对路径；改模板后要验证 wheel 里带上了它。
- 生成的用例会真的发请求：没有服务在监听时会抛 `ConnectionError`（WinError 10061），这是预期行为，用 `examples/mock_api.py` 可以本地试跑。
- 版本号三处必须同步：`pyproject.toml`、`__init__.py`、`CHANGELOG.md`。
- `pytest` 与 `requests` **刻意**放在核心依赖里（不是 `dev` 额外项）：目标是裸装
  `pip install openapi-crud-gen` 就能生成并跑通生成物。不要以"瘦身"为理由挪回 `dev`。

## 已知未验证项（不要假装验证过）

- Python 3.10 / 3.11：本机只有 3.14，仅靠 GitHub Actions 矩阵覆盖。
- `uv pip install -e .`：本机未装 uv。
- GitHub Actions：项目尚未 `git init`/推送，工作流只做过静态检查。
