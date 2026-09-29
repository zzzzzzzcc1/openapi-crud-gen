# 从零跑通一个完整例子

本文是一份**跟着敲就能跑通**的教程：从"启动一个服务"到"生成的测试全绿"，再到"接进 CI"。
所有命令和输出都是在本机真实执行过的（Windows + PowerShell，Python 3.14）；
macOS / Linux 只需把 `.\.venv\Scripts\python.exe` 换成 `.venv/bin/python`。

## 0. 先弄清三样东西

| 东西 | 是什么 | 本教程里是谁 |
| --- | --- | --- |
| 被测服务 | 你要测的那个 HTTP API，跑起来会监听某个地址 | `examples/tutorial/api.py`（示例后端） |
| OpenAPI 文档 | 服务的"说明书"，描述每个接口的路径、方法、请求体、响应码 | `examples/tutorial/openapi.yaml` |
| 测试项目 | 本工具生成测试骨架的地方 | `tests/generated/` |

本工具只做一件事：**读说明书 → 写测试骨架**。它不发请求、不管你的业务数据，这两件事留给你。

"部署"在这套流程里有两层含义，本文两件都做：

1. **第 2 步**：让被测服务跑起来，拿到一个地址（本地、容器、测试环境都行）。
2. **第 9 步**：把生成的测试接进 CI，让每次提交自动跑。

## 1. 准备环境

```powershell
cd C:\Users\a1802\Documents\Codex\2026-09-29\python-openapi-http-api-pytest-cli
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

装完确认一下：

```powershell
.\.venv\Scripts\openapi-crud-gen.exe --version
```

```
openapi-crud-gen, version 0.1.0
```

## 2. 启动被测服务（"部署"第一步）

教程自带一个只用标准库的示例后端，**它会认真校验输入**，所以后面能清楚看到"为什么必须填 TODO"：

```powershell
.\.venv\Scripts\python.exe examples\tutorial\api.py
```

```
tutorial API listening on http://127.0.0.1:8000 (Ctrl+C to stop)
```

**这个窗口别关**，它每收到一个请求就打印一行。真实项目里换成你自己的启动方式，例如：

```bash
uvicorn app.main:app --port 8000        # FastAPI
docker compose up api                   # 容器
# 或者直接用测试环境的地址，例如 https://test.example.com
```

你只需要记下**服务的地址**，下一步要用。

## 3. 先看会生成什么（`--dry-run`）

不写文件，先确认工具"看懂"了你的文档：

```powershell
.\.venv\Scripts\openapi-crud-gen.exe examples\tutorial\openapi.yaml --output-dir tests\generated --base-url http://127.0.0.1:8000 --dry-run
```

```
Loaded examples\tutorial\openapi.yaml (OpenAPI 3.0.3)
                        Recognized CRUD resources
+-----------------------------------------------------------------------+
| Resource | Base path | Actions                                        |
|----------+-----------+------------------------------------------------|
| users    | /users    | create, read_list, read_detail, update, delete |
+-----------------------------------------------------------------------+
would write tests\generated\test_users_crud.py
Dry run: 1 file(s), 0 endpoint(s) ignored
```

怎么读这段输出：

- `users`：文档里的 `/users` 被识别成一个资源。
- `Actions` 五个动作全齐：说明 `/users` 上的 GET/POST 和 `/users/{id}` 上的 GET/PUT/DELETE 都被认出来了。
- `0 endpoint(s) ignored`：没有接口被跳过（如果文档里有 `/users/{id}/posts` 这种嵌套路径，就会计入 ignored）。

## 4. 生成测试骨架

```powershell
.\.venv\Scripts\openapi-crud-gen.exe examples\tutorial\openapi.yaml --output-dir tests\generated --base-url http://127.0.0.1:8000
```

```
Generated 2 file(s) in tests\generated (0 skipped, 0 endpoint(s) ignored)

Next steps:
  1. Fill in the TODOs in the generated files (path parameters, request payload, assertions).
  2. Start your API at http://127.0.0.1:8000, or regenerate with a different --base-url.
  3. Run: pytest tests\generated
```

生成了两个文件：

```
tests/generated/
├── __init__.py            # 让 pytest 正常导入（自动生成）
└── test_users_crud.py     # 一个资源一个文件
```

## 5. 第一次跑：失败是正常的（关键理解点）

```powershell
.\.venv\Scripts\python.exe -m pytest tests\generated -q
```

```
FAILED tests/generated/test_users_crud.py::test_users_create - assert 400 in [201]
FAILED tests/generated/test_users_crud.py::test_users_read_detail - assert 404 in [200]
FAILED tests/generated/test_users_crud.py::test_users_update - assert 404 in [200]
FAILED tests/generated/test_users_crud.py::test_users_delete - assert 404 in [204]
4 failed, 1 passed in 0.31s
```

**这不是工具坏了**，是它诚实地告诉你"我还缺业务信息"。逐条看：

| 失败用例 | 实际返回 | 原因 |
| --- | --- | --- |
| `test_users_create` | 400 | 文档写了 `requestBody.required: [name]`，但骨架发的是 `json={}`——没带 name |
| `test_users_read_detail` | 404 | 骨架里是 `id = None`，URL 被拼成 `/users/None`，服务当然找不到 |
| `test_users_update` | 404 | 同上，路径参数还是 `None` |
| `test_users_delete` | 404 | 同上 |
| `test_users_read_list` | 200 ✅ | 这个接口既不需要路径参数也不需要请求体，所以骨架开箱即绿 |

看一眼服务端的窗口，能对上每条请求：

```
POST /users -> 400
GET /users -> 200
GET /users/None -> 404
PUT /users/None -> 404
DELETE /users/None -> 404
```

所以：**`TODO` 不是装饰，它是"这里必须有你的业务数据"的标记。**

## 6. 填 TODO：只有三种

打开 `tests/generated/test_users_crud.py`，你会看到三类 TODO：

| 你在文件里看到 | 该写什么 | 本教程填成 |
| --- | --- | --- |
| `id = None  # TODO: 替换路径参数` | 一个真实存在的 ID | `id = "1"` |
| `# TODO: 准备请求数据` + `json={}` | 符合文档 schema 的请求体 | `json={"name": "Grace"}` |
| `# TODO: 补充响应体断言` | 状态码之外的检查（可选） | 暂时留着不写也行 |

填完以后，三个函数长这样（其余同理）：

```python
def test_users_create():
    # TODO: 准备请求数据
    response = requests.post(f"{BASE_URL}/users", json={"name": "Grace"})
    assert response.status_code in [201]
    # TODO: 补充响应体断言


def test_users_read_detail():
    id = "1"  # TODO: 替换路径参数
    response = requests.get(f"{BASE_URL}/users/{id}")
    assert response.status_code in [200]
    # TODO: 补充响应体断言
```

`id = "1"` 里的 `"1"` 是那个示例后端自带的种子用户（`{"id": "1", "name": "Ada"}`）。
你自己的项目里，这里要换成数据库里真实存在的记录 ID，或者先调 create 造一条。

## 7. 再跑：全绿

```powershell
.\.venv\Scripts\python.exe -m pytest tests\generated -q
```

```
.....                                                                    [100%]
5 passed in 0.12s
```

到这里，一个资源的 CRUD 回归就跑通了。

## 8. 进阶：让用例串起来（骨架不生成，真实项目要）

骨架生成的 5 个用例彼此独立：`create` 拿到的 id 不会自动传给 `update`/`delete`。
真实项目通常用一个 fixture 造数据，再把它喂给后面的用例。新建
`tests/generated/test_users_flow.py`（手写，不被覆盖）：

```python
import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture
def created_user():
    response = requests.post(f"{BASE_URL}/users", json={"name": "Flow"})
    assert response.status_code == 201
    return response.json()


def test_created_user_can_be_read_back(created_user):
    response = requests.get(f"{BASE_URL}/users/{created_user['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "Flow"
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests\generated -q
```

```
......                                                                   [100%]
6 passed in 0.12s
```

这个例子也说明：**生成的文件可以随便改、可以再手写文件放在一起**，`--overwrite` 只会覆盖同名文件。

## 9. 多环境：把 BASE_URL 变成环境变量

骨架把 `BASE_URL` 写死在文件里。要在本地/测试/预发之间切换，改一行就行：

```python
import os

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
```

验证它真的生效（先故意指向一个没人监听的端口）：

```powershell
$env:BASE_URL="http://127.0.0.1:9999"; .\.venv\Scripts\python.exe -m pytest tests\generated -q -x
```

```
urllib3.exceptions.NewConnectionError: HTTPConnection(host='127.0.0.1', port=9999): Failed to establish a new connection
```

```powershell
$env:BASE_URL="http://127.0.0.1:8000"; .\.venv\Scripts\python.exe -m pytest tests\generated -q
```

```
......                                                                   [100%]
6 passed in 0.12s
```

## 10. 接进 CI（"部署"第二步）

思路：CI 里先让服务就绪，再生成 + 跑。服务有三种来源，按你的项目选一种：

| 来源 | 做法 |
| --- | --- |
| CI 里起容器 | `services:` 起 postgres/redis，`docker run` 起你的 API |
| CI 里起示例后端 | `python examples/tutorial/api.py &`（只适合跑通流程） |
| 指向测试环境 | 直接把 `BASE_URL` 指向已有的测试环境地址（记得放 secret） |

示意片段（**本仓库的 [test.yml](../.github/workflows/test.yml) 只跑单元测试，没有启用这段**）：

```yaml
      - name: Start the API under test
        run: python examples/tutorial/api.py &
      - name: Generate and run CRUD tests
        run: |
          openapi-crud-gen examples/tutorial/openapi.yaml \
            --output-dir tests/generated \
            --base-url http://127.0.0.1:8000
          pytest tests/generated -q
```

落地时的两个坑：

- 后台进程要等它真的起来（`for i in {1..20}; do curl -sf $BASE_URL/users && break; sleep 1; done`）。
- 生成的文件建议加进 `.gitignore`（本仓库就已忽略 `tests/generated/`），否则每次生成都在 diff 里刷一屏。

## 11. 常见问题

| 现象 | 原因 / 处理 |
| --- | --- |
| `ConnectionError: ... 由于目标计算机积极拒绝` | 服务没起来，或 `--base-url` 写错。先 `curl http://127.0.0.1:8000/users` 确认 |
| `ModuleNotFoundError: No module named 'requests'` | 跑 pytest 的解释器里没装：`pip install -e ".[dev]"` |
| 断言失败但接口"看起来没问题" | 用 `pytest -q -x` 看实际状态码；常见是文档与实现不一致（文档写 201，实现返回 200） |
| 提示 `skipped ... (exists)` | 默认不覆盖已有文件，确认要覆盖加 `--overwrite` |
| 想只跑某个资源 | `--resource-filter users`（多个用逗号分隔） |
| 想看会生成什么但不落盘 | `--dry-run` |

更多限制与已知问题见 [README](../README.md)。
