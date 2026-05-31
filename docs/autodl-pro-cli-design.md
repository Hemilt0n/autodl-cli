# AutoDL Pro CLI 调研、设计方案与实现计划

调研日期：2026-05-31

参考资料：

- AutoDL 容器实例 Pro API：https://www.autodl.com/docs/instance_pro_api/
- AutoDL 通用 API：https://www.autodl.com/docs/common_api/
- AutoDL 性能指标监控：https://www.autodl.com/docs/metric_monitor/

补充参考，暂不纳入第一版：

- AutoDL 弹性部署 API：https://www.autodl.com/docs/esd_api_doc/

## 1. 结论

可以开发一个 `autodl` CLI。基于官方公开 API，MVP 可以稳定覆盖：

- 账号 token 配置与校验。
- 查询账户余额。
- Pro 实例创建、列表、状态、详情、开机、关机、释放。
- 私有镜像保存、私有镜像列表。
- 基于轮询的本地监控、状态变化通知、余额告警、实例异常告警。
- 基于失败重试和退避策略的资源等待流程，主要用于稀缺卡型或指定地区无可用算力时重试。
- CLI 自身的 Webhook 通知配置与测试，第一版优先支持飞书和通用 Webhook。
- 交互式初始化配置。

已确认的第一版范围：

- 只做 Pro 实例，不实现弹性部署命令组。
- 使用 `uv` 管理 Python 项目和依赖。
- Pro 的算力和数据分离降低了“抢某台机器”的必要性；CLI 不需要抓取机器池，也不需要选择具体物理机器。
- 对稀缺资源仍保留 `hunt`/`wait` 类命令，含义是等待可用算力并重试开机或创建，而不是绕过平台调度。

需要明确的边界：

- AutoDL 文档没有提供“用户名密码登录”API；CLI 应使用开发者 Token，并通过余额接口或实例列表接口验证 token 有效性。
- Pro API 未看到独立的 Pro 库存查询接口；资源等待在 Pro 侧只能通过创建实例或开机实例的失败重试实现。
- “获取地区 GPU 库存”存在于弹性部署 API，并且文档说明弹性部署 API 需要企业认证。这个能力可以作为企业账号可选增强，而不能作为普通 Pro CLI 的基础能力。
- AutoDL 文档没有提供“配置平台侧 webhook”的接口；Webhook 应设计为 CLI 侧主动推送通知到用户配置的 `webhook_url`。
- 性能指标监控的完整 GPU 指标能力是企业认证后的功能，并且主要面向容器内本地接口或 Prometheus 推送。普通 Pro CLI 可以先使用 `snapshot.usage_info` 做远程轮询监控。

## 2. 官方 API 能力梳理

### 2.1 鉴权与基础信息

公共 Host：

```text
https://api.autodl.com
```

鉴权方式：

```http
Authorization: <developer_token>
```

Token 获取位置：AutoDL 控制台 -> 账号/设置 -> 开发者 Token。

### 2.2 账户余额

接口：

```http
POST /api/v1/dev/wallet/balance
```

能力：

- 获取当前余额。
- 获取累计消费。
- 获取代金券余额。

金额单位：

- API 返回的 `assets`、`accumulate`、`voucher_balance` 需要除以 `1000` 才是人民币元。

CLI 价值：

- `autodl account balance`。
- 初始化时验证 token。
- 资源等待前做余额下限保护。
- 监控时触发低余额通知。

### 2.3 Pro 实例

#### 创建实例

接口：

```http
POST /api/v1/dev/instance/pro/create
```

关键参数：

- `data_center_list`：可选，多个地区代码；不传则系统自动选择。
- `req_gpu_amount`：必填，GPU 数量，文档范围为 1 到 4。
- `expand_system_disk_by_gb`：必填，系统盘扩容 GB，文档范围为 0 到 500。
- `gpu_spec_uuid`：必填，算力规格 ID。
- `image_uuid`：必填，镜像 UUID。
- `cuda_v_from`：必填，CUDA 版本下限，例如 `113` 表示 `cuda >= 11.3`。
- `instance_name`：可选，实例备注名。
- `start_command`：可选，开机后执行命令。

限制：

- 文档示例说明默认按量计费创建，暂不支持选择其他计费方式创建。

CLI 价值：

- `autodl instance create`。
- `autodl hunt create` 通过反复调用 create 尝试抢到可用卡。
- 可加入本地费用保护，如余额下限、最大价格确认、最大尝试次数。

#### 获取实例详情

接口：

```http
GET /api/v1/dev/instance/pro/snapshot
```

参数：

- `instance_uuid`。

返回价值：

- 实例地区、价格、GPU 型号、芯片厂商、CPU 架构。
- `usage_info`：CPU 使用率、内存使用率、根文件系统占用、数据盘占用、镜像拉取进度等。
- SSH 连接信息。
- JupyterLab 地址与 token。
- 6006、6008 服务映射地址。

CLI 价值：

- `autodl instance inspect <uuid>`。
- `autodl instance ssh-cmd <uuid>`。
- `autodl instance jupyter <uuid>`。
- `autodl monitor watch <uuid>`。
- 状态页、通知消息中展示连接信息。

注意：

- `root_password`、`jupyter_token` 属于敏感信息，默认输出需要脱敏。除非用户传 `--show-secret`，否则不直接打印。

#### 获取实例状态

接口：

```http
GET /api/v1/dev/instance/pro/status
```

参数：

- `instance_uuid`。

CLI 价值：

- `autodl instance status <uuid>`。
- 监控状态变化。
- 资源等待成功后轮询等待进入 `running`。

#### 获取实例列表

接口：

```http
POST /api/v1/dev/instance/pro/list
```

参数：

- `page_index`。
- `page_size`。

返回价值：

- 实例 UUID、地区、状态、启动方式、计费方式、GPU 数量、名称、`gpu_spec_uuid`、分页信息。

CLI 价值：

- `autodl instance list`。
- `autodl instance list --all` 自动翻页。
- `autodl monitor all`。
- `autodl cleanup` 筛选停止或长时间运行实例。

边界与风险：

- 这个接口获取的是当前账号自己的 Pro 实例列表，不是 AutoDL 平台的物理机器列表，也不是全站可用算力库存。
- 作为官方公开接口，只读查询本身风险较低，适合用于 CLI 列表展示、监控和初始化校验。
- 风险主要来自过高频轮询、打印敏感连接信息、以及把列表结果写入不安全日志。CLI 应默认限速、脱敏 SSH 密码/Jupyter token，并支持 `--json` 但不默认输出密钥字段。
- 如果要获取“某地区某 GPU 还有多少库存”，Pro API 未看到对应接口；弹性部署文档中的 GPU 库存接口属于企业弹性部署能力，不放入第一版。

#### 开机实例

接口：

```http
POST /api/v1/dev/instance/pro/power_on
```

参数：

- `instance_uuid`。
- `payload`：文档中 `gpu` 表示有卡开机。
- `start_command`：可选，会覆盖创建时设置的命令。

限制：

- 文档说明暂不支持 API 以无卡模式开机。

CLI 价值：

- `autodl instance start <uuid>`。
- `autodl hunt start <uuid>` 反复尝试对一个已存在实例有卡开机。

#### 关机实例

接口：

```http
POST /api/v1/dev/instance/pro/power_off
```

参数：

- `instance_uuid`。

CLI 价值：

- `autodl instance stop <uuid>`。
- 自动关机策略。
- 余额保护策略。

#### 释放实例

接口：

```http
POST /api/v1/dev/instance/pro/release
```

参数：

- `instance_uuid`。

限制：

- 文档提示释放前应先关机，否则可能无法释放。

CLI 价值：

- `autodl instance release <uuid>`。
- `autodl instance destroy <uuid>`：先关机、等待停止、再释放。
- 批量清理停止实例。

### 2.4 Pro 镜像

#### 保存镜像

接口：

```http
POST /api/v1/dev/instance/pro/image/save
```

参数：

- `instance_uuid`。
- `image_name`。

返回：

- `image_uuid`。

CLI 价值：

- `autodl image save <instance_uuid> --name <name>`。
- 保存后轮询镜像列表，等待状态变为 `finished`。

#### 获取私有镜像列表

接口：

```http
POST /api/v1/dev/instance/pro/image/private/list
```

参数：

- `page_index`。
- `page_size`。

返回：

- `image_uuid`。
- `name`。
- `status`。
- `image_size`。
- `create_at`。

CLI 价值：

- `autodl image list`。
- `autodl image wait <image_uuid>`。
- 初始化向导中选择默认镜像。

限制：

- Pro 文档中没有看到删除镜像、重命名镜像、导入外部镜像的接口。CLI 先不承诺这些能力。

### 2.5 非第一版范围：弹性部署 API

弹性部署 API 与 Pro 实例 API 不同，文档说明需要企业认证。本项目第一版只做 Pro 实例，因此以下能力只作为边界说明，不进入命令设计和实现计划。

可选能力：

- 查询私有镜像：`POST /api/v1/dev/image/private/list`。
- 创建部署：`POST /api/v1/dev/deployment`。
- 查询部署、容器、容器事件。
- 停止容器、设置副本数量、停止部署、删除部署。
- 设置调度黑名单。
- 查询地区 GPU 库存：`POST /api/v1/dev/machine/region/gpu_stock`。

对本 CLI 的意义：

- 普通 Pro CLI 不能依赖这些接口。
- 不在第一版实现 `autodl esd ...` 命令组。
- 如果未来明确要支持企业账号，可以单独设计企业增强版，而不是混入 Pro MVP。

### 2.6 性能指标监控

官方性能指标监控文档标注仅企业认证账号可用。

两种方式：

- 容器内请求本地接口获取当前 CPU、内存、GPU 指标。
- 平台推送到用户自有 Prometheus PushGateway，再接 Grafana。

对本 CLI 的意义：

- 本地电脑运行的 CLI 无法直接调用容器内 `127.0.0.1` 监控接口，除非 CLI 通过 SSH 在容器内执行命令。
- MVP 先用 Pro `snapshot.usage_info` 做远程轮询监控。
- 进阶版支持 `autodl monitor ssh <uuid>`：通过 SSH 执行容器内监控脚本，获取更完整 GPU 指标。
- 企业用户可配置 Prometheus PushGateway，但这更像平台配置指导，不是 Pro CLI 核心能力。

## 3. 功能可行性分级

### P0：应立即实现

- `init` 交互式配置。
- Token 存储与验证。
- 余额查询。
- 实例列表、详情、状态。
- 实例创建、开机、关机、释放。
- 镜像保存、镜像列表。
- 标准化错误处理。
- Webhook 测试和发送。

### P1：高价值自动化

- 资源等待与重试：
  - 已有实例等待有卡开机。
  - 新实例等待创建成功。
  - 多地区、多规格候选。
  - 最大尝试次数、最大运行预算、余额下限。
  - 指数退避、随机抖动、速率限制。
- 监控：
  - 状态变化。
  - 长时间 `starting`。
  - CPU/内存/磁盘阈值。
  - 镜像拉取进度卡住。
  - 余额告警。
- 通知：
  - 通用 webhook。
  - 飞书 webhook 适配。

### P2：更完整的运维体验

- 本地后台守护进程。
- 定时开关机。
- 自动释放停止实例。
- 运行历史与费用估算。
- TUI 仪表盘。
- SSH/Jupyter 快捷打开。
- 镜像保存后自动等待完成并通知。

### P3：暂不纳入第一版

- 弹性部署命令组。
- 企业 GPU 库存查询。
- 基于库存的调度建议。
- 调度黑名单管理。
- 容器事件订阅和告警。
- Prometheus/Grafana 接入模板。

## 4. 推荐技术方案

### 4.1 语言与框架

推荐使用 Python。

理由：

- CLI、HTTP、交互式配置、JSON/TOML、跨平台打包生态成熟。
- AutoDL 官方示例也使用 Python `requests`，用户理解成本低。
- 后续可很容易加 SSH、Prometheus、Webhook、TUI。

推荐依赖：

- `typer`：CLI 命令声明。
- `httpx`：HTTP client，支持 timeout、retry 包装、测试 mock。
- `pydantic`：请求与响应模型。
- `rich`：表格、状态、日志、美化输出。
- `questionary` 或 `InquirerPy`：交互式初始化。
- `platformdirs`：跨平台配置目录。
- `keyring`：优先把 token 存到系统密钥链。
- `tomli-w` / `tomllib`：配置读写。
- `tenacity`：重试与退避。
- `APScheduler`：后续后台调度。
- `sqlite-utils` 或标准库 `sqlite3`：运行历史和监控状态。
- `pytest`、`respx`、`freezegun`：测试。

环境管理：

- 使用 `uv init --package --app --name autodl-cli --vcs none --build-backend uv` 初始化项目。
- 使用 `uv add ...` 管理运行依赖，使用 `uv add --dev ...` 管理测试和格式化依赖。
- 项目包名保留 `autodl-cli`，命令入口同时提供 `autodl` 和 `autodl-cli`，日常文档以 `autodl` 为主。

### 4.2 项目结构

建议结构：

```text
autodl-cli/
  pyproject.toml
  README.md
  docs/
    autodl-pro-cli-design.md
  src/
    autodl_cli/
      __init__.py
      __main__.py
      app.py
      config.py
      constants.py
      errors.py
      output.py
      api/
        __init__.py
        client.py
        models.py
        account.py
        instance_pro.py
        image.py
        esd.py
      commands/
        __init__.py
        init.py
        account.py
        instance.py
        image.py
        monitor.py
        hunt.py
        webhook.py
        schedule.py
      services/
        monitor.py
        hunt.py
        notifier.py
        scheduler.py
        state_store.py
        secrets.py
      webhooks/
        base.py
        generic.py
        feishu.py
        dingtalk.py
        wecom.py
  tests/
    test_api_client.py
    test_config.py
    test_hunt.py
    test_monitor.py
    test_webhook.py
```

### 4.3 配置文件与密钥存储

配置文件路径：

- macOS：`~/Library/Application Support/autodl-cli/config.toml`
- Linux：`~/.config/autodl-cli/config.toml`
- Windows：`%APPDATA%\autodl-cli\config.toml`

状态数据库路径：

- macOS：`~/Library/Application Support/autodl-cli/state.db`
- Linux：`~/.local/share/autodl-cli/state.db`
- Windows：`%LOCALAPPDATA%\autodl-cli\state.db`

Token 存储策略：

1. 默认使用系统 keyring。
2. 如果 keyring 不可用，提示用户是否允许写入配置文件。
3. 写入配置文件时，权限设置为当前用户可读写。
4. 命令输出永远不打印完整 token。

配置示例：

```toml
[profile.default]
base_url = "https://api.autodl.com"
default_data_centers = ["westDC3", "beijingDC2"]
default_gpu_spec_uuid = "pro6000-p"
default_gpu_amount = 1
default_image_uuid = "base-image-l2t43iu6uk"
default_cuda_v_from = 118
default_expand_system_disk_by_gb = 0

[profile.default.safety]
min_balance_yuan = 20
max_attempts = 200
min_retry_interval_seconds = 20
max_retry_interval_seconds = 180
max_continuous_runtime_minutes = 0
require_confirm_for_release = true

[[profile.default.webhooks]]
name = "default"
type = "generic"
url = "https://example.com/webhook"
enabled = true
events = [
  "hunt.succeeded",
  "hunt.failed",
  "instance.running",
  "instance.stopped",
  "monitor.alert",
  "balance.low"
]
```

## 5. CLI 命令设计

### 5.1 全局参数

```text
autodl [OPTIONS] COMMAND

Options:
  --profile TEXT       配置 profile，默认 default
  --config PATH        指定配置文件
  --base-url TEXT      覆盖 API base URL
  --token TEXT         临时 token，不落盘
  --json               输出 JSON，方便脚本集成
  --debug              打印调试日志，敏感字段仍脱敏
  --no-color           关闭彩色输出
```

### 5.2 初始化与配置

```text
autodl init
autodl config show
autodl config path
autodl config set KEY VALUE
autodl config profiles
autodl config use PROFILE
autodl auth check
```

`autodl init` 交互流程：

1. 选择或创建 profile。
2. 输入开发者 Token。
3. 选择 token 存储方式。
4. 调用余额接口验证 token。
5. 拉取私有镜像列表，允许选择默认镜像。
6. 选择默认 GPU 规格：
   - 使用内置 Pro 附录中的规格。
   - 或手动输入 `gpu_spec_uuid`。
7. 选择默认地区列表。
8. 配置 CUDA 版本下限。
9. 配置系统盘扩容。
10. 配置安全策略：
    - 余额下限。
    - 资源等待最大尝试次数。
    - 资源等待间隔。
    - 释放实例是否强制确认。
11. 配置 Webhook：
    - 不配置。
    - 通用 Webhook。
    - 飞书。
12. 发送测试通知。
13. 展示最终摘要，不打印敏感字段。

### 5.3 账户

```text
autodl account balance
```

输出示例：

```text
Balance
  cash: 128.35 CNY
  voucher: 20.00 CNY
  spent: 913.42 CNY
```

### 5.4 实例

```text
autodl instance list [--all] [--status running] [--page-size 20]
autodl instance status INSTANCE_UUID
autodl instance inspect INSTANCE_UUID [--show-secret]
autodl instance create [OPTIONS]
autodl instance start INSTANCE_UUID [--start-command CMD] [--wait]
autodl instance stop INSTANCE_UUID [--wait]
autodl instance release INSTANCE_UUID [--yes]
autodl instance destroy INSTANCE_UUID [--yes]
autodl instance ssh-cmd INSTANCE_UUID [--copy]
autodl instance jupyter INSTANCE_UUID [--show-token]
```

`create` 参数：

```text
--data-center TEXT        可重复，例如 --data-center westDC3
--gpu-spec-uuid TEXT
--gpu-amount INTEGER
--image-uuid TEXT
--cuda-v-from INTEGER
--disk-gb INTEGER
--name TEXT
--start-command TEXT
--wait
```

`destroy` 行为：

1. 查询当前状态。
2. 如果运行中，先关机。
3. 轮询等待停止。
4. 调用释放。
5. 发送通知。

### 5.5 镜像

```text
autodl image list [--all] [--status finished]
autodl image save INSTANCE_UUID --name NAME [--wait]
autodl image wait IMAGE_UUID [--timeout 3600]
```

后续如官方增加删除/重命名接口，再加：

```text
autodl image delete IMAGE_UUID
autodl image rename IMAGE_UUID NAME
```

### 5.6 资源等待与重试

Pro 实例是算力和数据分离模型，CLI 不需要抢某台固定机器，也不需要获取平台机器池。这里的 `hunt` 命令只表示在稀缺 GPU、指定地区或调度暂时失败时，按安全频率等待可用算力并重试。

两种模式：

#### 5.6.1 等待已有实例有卡开机

```text
autodl hunt start INSTANCE_UUID \
  --interval 30 \
  --max-attempts 200 \
  --max-interval 180 \
  --start-command "bash /root/start.sh" \
  --notify
```

流程：

1. 验证余额。
2. 查询实例当前状态。
3. 如果已 running，直接成功。
4. 调用 `power_on`。
5. 失败时识别是否库存/调度类错误。
6. 按退避策略等待。
7. 成功后轮询状态到 running。
8. 发送成功通知，包含 SSH/Jupyter 信息。

#### 5.6.2 等待创建新实例

```text
autodl hunt create \
  --gpu-spec-uuid pro6000-p \
  --gpu-amount 1 \
  --image-uuid base-image-l2t43iu6uk \
  --cuda-v-from 118 \
  --data-center westDC3 \
  --data-center beijingDC2 \
  --disk-gb 0 \
  --name train-4090 \
  --interval 30 \
  --max-attempts 200 \
  --notify
```

流程：

1. 验证配置和余额。
2. 根据候选地区和规格构造请求。
3. 调用 create。
4. 失败时重试。
5. 成功拿到 instance UUID 后进入 wait。
6. 记录本地等待任务结果。
7. 通知成功或失败。

安全策略：

- 默认最小间隔不低于 20 到 30 秒。
- 加随机抖动，避免固定频率请求。
- 默认有最大尝试次数。
- 默认有余额下限保护。
- 不绕过平台风控，不抓取未公开接口，不模拟网页登录。
- 不 fetch 平台物理机器列表；只使用官方 Pro 实例接口和当前账号实例列表接口。

### 5.7 监控

```text
autodl monitor watch INSTANCE_UUID \
  --interval 60 \
  --cpu-alert 90 \
  --mem-alert 90 \
  --root-disk-alert 85 \
  --notify

autodl monitor all --interval 60 --notify
autodl monitor once INSTANCE_UUID
```

MVP 监控指标：

- 实例状态。
- `usage_info.cpu_usage_percent`。
- `usage_info.mem_usage_percent`。
- `root_fs_used_size / root_fs_total_size`。
- `data_disk_used_size / data_disk_total_size`。
- 镜像拉取/下载进度。
- SSH/Jupyter 地址是否出现。

告警规则：

- 状态从 running 变成非 running。
- 长时间 starting。
- CPU/内存持续超过阈值。
- 根盘持续超过阈值。
- `usage_info.valid` 长时间为 false。
- 镜像拉取进度长时间不变。
- 余额低于阈值。

状态存储：

- SQLite 记录上一次状态、上一次通知时间、指标采样。
- 同一告警按 `dedupe_key` 做冷却，避免刷屏。

### 5.8 Webhook

```text
autodl webhook add NAME --type generic --url URL
autodl webhook add NAME --type feishu --url URL
autodl webhook list
autodl webhook test NAME
autodl webhook remove NAME
```

通用 Webhook 请求：

```json
{
  "source": "autodl-cli",
  "event": "hunt.succeeded",
  "severity": "info",
  "profile": "default",
  "timestamp": "2026-05-31T09:00:00+08:00",
  "title": "AutoDL 可用算力等待成功",
  "message": "实例 pro-xxx 已进入 running",
  "data": {
    "instance_uuid": "pro-xxx",
    "status": "running",
    "gpu_spec_uuid": "pro6000-p"
  }
}
```

飞书 Webhook 请求：

- 第一版使用飞书机器人支持的 `msg_type = "text"` 或 `msg_type = "interactive"`。
- 默认用 `text`，减少格式兼容风险。
- 通知内容由同一套内部事件模型渲染，不把飞书格式暴露给业务层。
- 其他 Webhook 使用上面的通用 JSON 格式。

推荐事件：

- `auth.checked`
- `balance.low`
- `instance.created`
- `instance.running`
- `instance.stopped`
- `instance.released`
- `image.saved`
- `image.ready`
- `hunt.started`
- `hunt.succeeded`
- `hunt.failed`
- `monitor.alert`
- `monitor.recovered`

Webhook 安全：

- 支持自定义 Header。
- 支持 HMAC 签名。
- 支持超时和重试。
- 支持冷却和去重。
- 默认不发送 `root_password`、`jupyter_token`。

## 6. 内部设计

### 6.1 API Client

核心接口：

```python
class AutoDLClient:
    def balance(self) -> Balance: ...
    def list_instances(self, page_index: int, page_size: int) -> Page[InstanceSummary]: ...
    def get_instance_status(self, instance_uuid: str) -> str: ...
    def get_instance_snapshot(self, instance_uuid: str) -> InstanceSnapshot: ...
    def create_instance(self, request: CreateInstanceRequest) -> str: ...
    def power_on(self, instance_uuid: str, start_command: str | None = None) -> None: ...
    def power_off(self, instance_uuid: str) -> None: ...
    def release(self, instance_uuid: str) -> None: ...
    def save_image(self, instance_uuid: str, image_name: str) -> str: ...
    def list_private_images(self, page_index: int, page_size: int) -> Page[PrivateImage]: ...
```

处理规则：

- 统一 base URL。
- 统一 Authorization header。
- 统一 timeout，默认 30 秒。
- 统一解析 `code != "Success"` 为异常。
- 异常包含 `request_id`、HTTP status、AutoDL code、message。
- 敏感字段脱敏。

### 6.2 错误分类

建议错误类型：

- `AutoDLHTTPError`：HTTP 非 2xx。
- `AutoDLAPIError`：API 返回 `code != Success`。
- `AutoDLAuthError`：鉴权失败。
- `AutoDLRateLimitError`：频率限制或疑似频率限制。
- `AutoDLCapacityError`：无可用资源、库存不足、调度失败。
- `AutoDLValidationError`：本地参数校验失败。
- `AutoDLConfigError`：配置缺失。

资源等待时只有 `Capacity`、部分网络错误、部分 5xx 可重试；鉴权失败、参数错误、余额不足不应重试。

由于官方错误码文档不完整，第一版需要保留原始错误文本，并通过测试/实用反馈逐步补充错误分类规则。

### 6.3 输出层

默认人类可读：

- 实例列表使用 Rich table。
- 详情按分组输出。
- 敏感字段默认显示为 `******`。

脚本友好：

- 所有命令支持 `--json`。
- 成功退出码 `0`。
- 可重试失败可用退出码 `75`。
- 参数/config 错误退出码 `2`。
- 鉴权错误退出码 `77`。

### 6.4 State Store

SQLite 表：

```sql
profiles(name, created_at, updated_at)
monitor_samples(id, profile, instance_uuid, sampled_at, status, cpu, mem, root_disk, raw_json)
alerts(id, profile, dedupe_key, severity, first_seen_at, last_seen_at, last_sent_at, status, payload_json)
hunt_jobs(id, profile, mode, target_json, status, attempts, started_at, ended_at, result_json)
webhook_deliveries(id, profile, webhook_name, event, status, attempts, created_at, response_code, error)
```

### 6.5 交互式配置校验

`init` 阶段的校验：

- Token 非空。
- 余额接口可访问。
- 默认镜像 UUID 存在或用户确认手动输入。
- `gpu_spec_uuid` 在内置表中，或用户确认手动输入。
- `cuda_v_from` 是整数，例如 113、118、120。
- 系统盘扩容 0 到 500。
- Webhook URL 是 HTTP/HTTPS。
- 测试通知返回 2xx 才默认启用；否则询问是否仍然保存。

## 7. 测试计划

单元测试：

- 配置读写。
- Token 获取优先级。
- 响应模型解析。
- 金额单位转换。
- 敏感字段脱敏。
- AutoDL 错误分类。
- Webhook payload。
- 资源等待退避策略。
- 告警去重。

HTTP mock 测试：

- 每个 API 成功路径。
- HTTP 401/403。
- `code != Success`。
- 5xx 重试。
- 超时。
- 分页自动拉取。

集成测试：

- 用用户提供的真实 token 做只读接口测试：
  - `account balance`
  - `instance list`
  - `image list`
- 涉及计费的创建/开机/释放测试必须显式启用：
  - 环境变量 `AUTODL_ENABLE_BILLABLE_TESTS=1`
  - 二次确认。

不应默认跑真实创建实例测试，避免误产生费用。

## 8. 实现计划

### 阶段 0：项目骨架

目标：

- 创建 Python 包结构。
- 配置 `pyproject.toml`。
- 接入 `ruff`、`mypy`、`pytest`。
- 提供 `autodl --help`。

交付：

- 可安装本地 CLI。
- CI 或本地测试命令。

### 阶段 1：配置与账户

目标：

- `autodl init`。
- `autodl auth check`。
- `autodl account balance`。
- keyring/token/config 支持。

验收：

- 无 token 时给出清晰提示。
- token 有效时能显示余额。
- token 不打印明文。

### 阶段 2：Pro 实例基础命令

目标：

- `instance list/status/inspect/create/start/stop/release/destroy`。
- `--json` 支持。
- 分页支持。
- `--wait` 支持。

验收：

- mock 测试覆盖所有接口。
- 真实 token 下只读命令可运行。
- 计费命令需要确认。

### 阶段 3：镜像管理

目标：

- `image list/save/wait`。
- 镜像保存状态轮询。

验收：

- 可保存实例镜像。
- 保存完成通知。

### 阶段 4：Webhook 通知

目标：

- 通用 Webhook。
- 飞书 Webhook 适配。
- 测试命令。
- 告警去重和冷却。

验收：

- `webhook test` 可用。
- 每类事件 payload 稳定。
- 默认不泄漏敏感字段。

### 阶段 5：监控

目标：

- `monitor once/watch/all`。
- 状态、CPU、内存、磁盘、余额告警。
- SQLite 状态存储。

验收：

- 状态变化只通知一次。
- 告警恢复可通知。
- 网络短暂失败不导致进程退出。

### 阶段 6：资源等待与重试

目标：

- `hunt start`。
- `hunt create`。
- 退避、最大尝试、余额保护。
- 成功后 wait running。

验收：

- 可在 mock 下模拟前 N 次失败、第 N+1 次成功。
- 可中断，保留任务记录。
- 不对不可重试错误继续刷请求。

### 阶段 7：后台化与定时任务

目标：

- `schedule add/list/remove/run`。
- `daemon start/stop/status` 或给出 systemd/launchd 模板。
- 定时开关机。

验收：

- 能在本机长期运行。
- 崩溃重启后可恢复任务。

### 阶段 8：暂不纳入第一版

目标：

- 暂不实现企业弹性部署 API。
- 暂不实现平台库存查询。
- 如未来要做，单独设计 `esd` 命令组。

验收：

- Pro CLI 不依赖企业权限。
- 文档清楚说明 Pro API 只能获取当前账号实例列表，不能获取平台机器库存。

## 9. 值得新增但需要确认的功能

我建议讨论这些功能是否进入第一版：

1. 多账号/多 profile：适合管理多个 AutoDL 账号或团队 token。
2. 资源等待策略模板：例如 `cheap-4090`、`fast-h800`、`night-job`。
3. 自动关机保护：监控到低 GPU/CPU 使用率持续 N 分钟后关机。
4. 费用预算保护：按实例价格和运行时长估算，超过预算提醒或关机。
5. SSH 快捷能力：复制 SSH 命令、直接执行 `ssh`、通过 SSH 取 GPU 指标。
6. TUI 仪表盘：`autodl tui` 查看实例、余额、等待任务、告警。
7. JSON/YAML 任务文件：用声明式文件启动等待重试或批量实例。
8. Slack/Telegram/ServerChan/PushPlus 通知适配。
9. Docker 镜像：让 CLI 能在服务器或 NAS 上常驻运行。
10. 只读安全模式：只允许查询，不允许创建、开机、释放等计费/破坏操作。

## 10. 需要你确认的问题

实现前建议确认：

1. 是否需要长期后台进程？还是第一版只做前台命令和 watch？
2. Token 存储是否接受默认使用系统 keyring？如果 keyring 不可用，是否允许明文写入本地配置文件？
3. 默认语言和输出是否用中文？命令名建议仍用英文。
4. 是否有真实 AutoDL token 可用于只读接口联调？没有也可以先用 mock 完成。
5. 是否要把“自动低利用率关机”放进第一版？这是省钱但有误关风险的功能。
6. 是否要提供 Docker 部署方式，让监控/等待重试在云服务器上长期运行？

## 11. 推荐第一版范围

建议第一版目标：

- 技术栈：Python + uv + Typer + httpx + pydantic + rich。
- 命令：
  - `init`
  - `auth check`
  - `account balance`
  - `instance list/status/inspect/create/start/stop/release/destroy`
  - `image list/save`
  - `webhook test`
  - `monitor watch`
  - `hunt start`
  - `hunt create`
- 不做：
  - 企业弹性部署完整管理和库存查询。
  - 平台侧 webhook 配置。
  - 镜像删除/重命名。
  - 无卡开机。
  - 绕过官方 API 的网页登录或页面抓取。

这个范围可以较快做出可用工具，同时避免碰到权限和计费风险不清的问题。
