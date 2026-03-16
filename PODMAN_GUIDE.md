# Podman Compose 使用指南

本指南说明如何使用 Podman Compose 运行 pdf2pptx 项目。

---

## 如何使用 Podman + GPU 運行這份專案

若要在 **Podman** 下啟用 **NVIDIA GPU** 跑 inpaint-service，請依下列步驟操作。

### 前置條件

1. **NVIDIA 驅動**：主機已安裝並可執行 `nvidia-smi`。
2. **NVIDIA Container Toolkit（Podman 用）**：讓 Podman 容器能存取 GPU。
   - Linux 安裝：<https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>
   - 若用 RHEL/CentOS/Fedora：<https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#installing-on-rhel-centos-7-8>
3. **Podman 4.1+** 與 **podman compose**（或獨立 `podman-compose`）。

### 驗證 GPU 是否可在容器內使用

```bash
podman run --rm --device nvidia.com/gpu=all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

若能看到 GPU 資訊，表示環境正確。

### 啟動專案（Podman + GPU）

在專案根目錄執行：

```bash
# 先合併 base + GPU 設定，再套用 Podman 專用 GPU 覆寫（用 devices 傳 GPU）
podman compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.podman-gpu.yml up --build
```

- `docker-compose.yml`：所有服務（CPU 版）。
- `docker-compose.gpu.yml`：inpaint 使用 GPU 版 Dockerfile 與環境變數。
- `docker-compose.podman-gpu.yml`：為 Podman 加上 `devices: nvidia.com/gpu=all`（因 Podman 不認 `deploy.resources.reservations.devices`）。

後台執行可改為：

```bash
podman compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.podman-gpu.yml up --build -d
```

### 若使用舊版或獨立的 podman-compose

```bash
podman-compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.podman-gpu.yml up --build
```

### 存取位址

- **前端**：<http://localhost:5173>
- **後端 API 文件**：<http://localhost:8000/docs>
- **健康檢查**：<http://localhost:8000/health>

### 常見問題（Podman + GPU）

- **容器內看不到 GPU**：確認已加上 `-f docker-compose.podman-gpu.yml`，且主機 `nvidia-smi` 與上述 `podman run ... nvidia-smi` 皆正常。
- **nvidia-container-toolkit 未安裝**：請依官方文件為「Podman」安裝，不要只裝 Docker 版。
- **Windows**：GPU 透傳通常需 WSL2 + 在 WSL2 內安裝 NVIDIA 驅動與 Podman（或使用 Linux 實機/VM）。

---

## 什么是 Podman？

**Podman** 是一个无守护进程的 Docker 替代品，具有以下特点：
- ✅ 无需特权守护进程（更安全）
- ✅ 100% Docker CLI 兼容
- ✅ 支持 Pod（Linux 容器原生概念）
- ✅ 对 Windows/macOS 的原生支持
- ✅ 完整的 rootless 模式支持

---

## 快速开始

### 1. 安装 Podman 和 Podman Compose

#### Windows (PowerShell)
```powershell
# 使用 scoop
scoop install podman podman-compose

# 或使用 choco
choco install podman podman-compose

# 或使用 WSL 2（推荐）
# 在 WSL 2 中：
curl -fsSL https://get.docker.com/rootless | sh
sudo apt-get install podman-compose
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install podman podman-compose

# Fedora/RHEL/CentOS
sudo dnf install podman podman-compose
```

#### macOS
```bash
brew install podman podman-compose
```

### 2. 启动 Podman 服务

```bash
# macOS/Windows (使用 Podman Desktop)
# 启动 Podman Desktop 应用

# Linux
sudo systemctl start podman
sudo systemctl enable podman

# 验证安装
podman version
podman-compose version
```

### 3. 启动 pdf2pptx 系统

```bash
cd /path/to/pdf2pptx

# 启动所有服务（后台运行）
podman-compose up -d

# 查看服务状态
podman-compose ps
```

**预期输出：**
```
NAME                      IMAGE                       COMMAND                  STATUS
pdf2pptx-backend-1        pdf2pptx-backend:latest     "uvicorn app.main:a..."  Up 2 seconds
pdf2pptx-frontend-1       pdf2pptx-frontend:latest    "npm run dev"            Up 3 seconds
pdf2pptx-ocr-service-1    pdf2pptx-ocr-service:la...  "python main.py"         Up 2 seconds
pdf2pptx-inpaint-service-1 pdf2pptx-inpaint-service... "uvicorn main:app"       Up 4 seconds
```

### 4. 访问应用

- **前端**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **OCR 服务**: http://localhost:8001 (内部)
- **Inpaint 服务**: http://localhost:8002 (内部)

---

## 常用命令

### 基本操作

```bash
# 启动所有服务
podman-compose up -d

# 启动指定服务
podman-compose up -d inpaint-service

# 查看日志
podman-compose logs -f              # 所有服务
podman-compose logs -f inpaint-service  # 指定服务
podman-compose logs -f --tail=50    # 最后 50 行

# 停止服务
podman-compose stop                 # 停止所有
podman-compose stop inpaint-service # 停止指定

# 重启服务
podman-compose restart inpaint-service

# 停止并删除容器
podman-compose down                 # 保留数据
podman-compose down -v              # 删除数据和卷

# 重建镜像
podman-compose build --no-cache
```

### 查看信息

```bash
# 查看服务状态
podman-compose ps

# 执行命令进入容器
podman-compose exec inpaint-service bash

# 查看容器资源使用
podman stats

# 查看详细信息
podman-compose config
```

### 日志和调试

```bash
# 实时日志
podman-compose logs -f

# 查看指定行数
podman-compose logs -f --tail 100

# 保存日志到文件
podman-compose logs > docker-compose.log 2>&1

# 查看特定服务的详细日志
podman-compose logs -f inpaint-service | grep "ERROR"
```

---

## 配置调优

### 环境变量配置

创建 `.env` 文件来覆盖默认配置：

```env
# .env
INPAINT_SIZE=512
INPAINT_STEPS=25
INPAINT_TIMEOUT=300
MAX_PDF_PAGES=5
```

然后启动：
```bash
podman-compose --env-file .env up -d
```

### 资源限制

编辑 `docker-compose.yml` 添加资源限制：

```yaml
inpaint-service:
  build: ./inpaint-service
  expose:
    - "8002"
  deploy:
    resources:
      limits:
        cpus: '4'           # 最多使用 4 个 CPU
        memory: 8G          # 最多使用 8GB 内存
      reservations:
        cpus: '2'
        memory: 4G
```

然后重启：
```bash
podman-compose up -d --remove-orphans
```

### GPU 支持

使用 GPU 加速（NVIDIA）：

```bash
# 1. 确保 NVIDIA Container Toolkit 已安装
podman run --rm --name ubuntu1 \
  nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi

# 2. 使用 GPU 版本 Dockerfile
podman-compose -f docker-compose.gpu.yml build

# 3. 启动时启用 GPU
podman-compose -f docker-compose.gpu.yml up -d
```

如果没有现成的 `docker-compose.gpu.yml`，创建一个：

```yaml
# docker-compose.gpu.yml
version: '3.8'

services:
  inpaint-service:
    build:
      context: ./inpaint-service
      dockerfile: Dockerfile.gpu
    expose:
      - "8002"
    environment:
      - INPAINT_SIZE=1024
      - INPAINT_STEPS=50
      - HF_HOME=/data/hf-cache
    volumes:
      - hf-cache:/data/hf-cache
    device:
      - nvidia.com/gpu=all

volumes:
  hf-cache:
```

启动：
```bash
podman-compose -f docker-compose.gpu.yml up -d
```

---

## 故障排除

### 问题 1: "Cannot find service"

**错误**: 
```
Error: service "inpaint-service" not found
```

**解决**:
```bash
# 重建容器
podman-compose down --remove-orphans
podman-compose up --build -d

# 查看镜像
podman images
```

### 问题 2: 端口被占用

**错误**:
```
Error: trying to bind to [0.0.0.0:8002]: listen tcp: bind: Only one usage of each socket address 
```

**解决**:
```bash
# 查看占用端口的进程
podman ps -a | grep 8002

# 清理
podman stop $(podman ps -aq --filter "expose=8002")
podman rm $(podman ps -aq --filter "expose=8002")

# 修改 docker-compose.yml 中的端口
# ports:
#   - "8003:8002"  # 改用 8003

podman-compose up -d
```

### 问题 3: 文件权限错误

**错误**:
```
Permission denied: /data/hf-cache
```

**原因**: Podman 在 rootless 模式下，容器内的文件权限需要匹配

**解决**:
```bash
# 方法 1: 修改卷的权限
podman run --rm -v hf-cache:/data/hf-cache alpine chmod 777 /data/hf-cache

# 方法 2: 在 compose 中指定用户
inpaint-service:
  user: "1000:1000"  # 使用当前用户 ID
  volumes:
    - hf-cache:/data/hf-cache:Z  # Z 标志允许访问
```

### 问题 4: 网络连接失败

**错误**:
```
Cannot resolve service 'ocr-service'
```

**原因**: Podman 网络隔离

**解决**:
```bash
# 重建网络
podman-compose down
podman network prune  # 清理<unused networks
podman-compose up -d

# 或显式创建网络
podman network create pdf2pptx-net
podman-compose --project-name pdf2pptx up -d

# 检查网络
podman network inspect pdf2pptx_default
```

### 问题 5: 模型下载超时

**现象**: 容器一直重启，日志显示超时

**解决**:
```bash
# 预先下载模型（使用网络较好的环境）
podman run --rm \
  -v hf-cache:/data/hf-cache \
  -e HF_HOME=/data/hf-cache \
  python:3.10 \
  bash -c "pip install diffusers && \
    python -c 'from diffusers import StableDiffusionInpaintPipeline; \
    StableDiffusionInpaintPipeline.from_pretrained(\"runwayml/stable-diffusion-inpainting\")'"

# 然后启动
podman-compose up -d
```

### 问题 6: Windows 上缺少 WSL2 / Hyper-V

**解决**:
```powershell
# 检查虚拟化支持
Get-ComputerInfo | Select-Object -Property HyperVRequirementVirtualizationFirmwareEnabled

# 启用 Hyper-V (需要重启)
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# 重启
Restart-Computer
```

---

## Podman vs Docker Compose

| 特性 | Docker | Podman |
|------|--------|--------|
| 守护进程 | ✅ 需要 docker daemon | ❌ 无守护进程 |
| 权限需求 | ✅ 需要 sudo | ❌ 可 rootless 运行 |
| CLI 兼容性 | - | ✅ 100% 兼容 |
| 容器网络 | ✅ 成熟 | ✅ 完整 |
| GPU 支持 | ✅ 完整 | ⚠️ NVIDIA Container Toolkit |
| Pod 支持 | ❌ Docker Swarm | ✅ 原生支持 |
| 速度 | ⚠️ 守护进程开销 | ✅ 更快 |

---

## 高级用法

### 使用 Podman Pod 运行多个容器

创建 `podman-compose.pod.yml`:

```yaml
version: '3'
services:
  backend:
    image: pdf2pptx-backend
    ports:
      - "8000:8000"
    pod: pdf2pptx

  inpaint-service:
    image: pdf2pptx-inpaint
    pod: pdf2pptx

  ocr-service:
    image: pdf2pptx-ocr
    pod: pdf2pptx

pods:
  pdf2pptx:
    ports:
      - "8000:8000"
      - "8001:8001"
      - "8002:8002"
```

启动：
```bash
podman-compose -f podman-compose.pod.yml up -d
```

### Rootless 模式最佳实践

```bash
# 1. 启用 rootless 模式
podman system migrate --new-config

# 2. 配置 subuid/subgid
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER

# 3. 启用用户命名空间
echo "user.max_user_namespaces=7675" | sudo tee -a /etc/sysctl.d/podman.conf
sudo sysctl -p /etc/sysctl.d/podman.conf

# 4. 启动 rootless 服务
systemctl --user enable podman
systemctl --user start podman

# 5. 设置 DOCKER_HOST
export DOCKER_HOST=unix:///var/run/user/$(id -u)/podman/podman.sock
```

### 与 Podman Desktop 集成

Podman Desktop 是 Podman 的 GUI，支持 Compose：

1. 下载并安装 [Podman Desktop](https://podman-desktop.io/)
2. 打开应用并导入项目文件夹
3. 在 UI 中启动/停止服务
4. 查看实时日志和容器统计

---

## 性能对比

### 启动时间（本地机器）

| 方案 | 时间 |
|------|------|
| Docker（守护进程运行） | ~3-5 秒 |
| Podman（Rootless） | ~4-6 秒 |
| Podman Desktop | ~2-3 秒 |

### 内存占用

| 方案 | 基础 | 运行时 |
|------|------|--------|
| Docker | ~150 MB (daemon) | +4-5 GB |
| Podman (rootless) | 0 MB | +3-4 GB |

---

## 参考资源

- [Podman 官方文档](https://podman.io/docs)
- [Podman Compose GitHub](https://github.com/containers/podman-compose)
- [Podman Desktop](https://podman-desktop.io/)
- [Container Standards (OCI)](https://opencontainers.org/)

---

## 总结

**Podman Compose 命令速查**：

```bash
# 启动
podman-compose up -d

# 查看状态
podman-compose ps

# 查看日志
podman-compose logs -f

# 停止
podman-compose down

# 清理
podman-compose down -v
```

**快速切换**：如果已经熟悉 Docker，只需将所有 `docker-compose` 改为 `podman-compose` 即可！
