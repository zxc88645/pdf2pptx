# Inpaint Service

基于 Stable Diffusion Inpainting 的图像修复服务，用于移除 PDF 文本区域并填充背景。

## 功能

- **POST /inpaint** - 接收图像和遮罩，返回修复后的图像
- **GET /health** - 健康检查，显示设备状态和模型加载情况

## API 端点

### GET /health

健康检查端点。

**响应示例：**
```json
{
  "status": "ready",
  "device": "cuda",
  "model_loaded": true
}
```

**状态说明：**
- `status: "ready"` - 服务就绪，可处理请求
- `status: "initializing"` - 模型加载中，请稍候
- `device: "cuda"` - 使用 GPU（快速）
- `device: "cpu"` - 使用 CPU（缓慢，不推荐）

### POST /inpaint

发送图像和遮罩进行修复。

**请求：**
- `image` (multipart/form-data) - 输入图像 (PNG/JPG)
- `mask` (multipart/form-data) - 遮罩图像 (PNG/JPG)
  - 白色像素 (255) = 需要修复的区域
  - 黑色像素 (0) = 保留的区域

**响应：**
- Content-Type: `image/png`
- Body: PNG 格式的修复后的图像

**示例请求：**
```bash
curl -X POST http://localhost:8002/inpaint \
  -F "image=@input.png" \
  -F "mask=@mask.png" \
  -o output.png
```

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `INPAINT_MODEL_ID` | `runwayml/stable-diffusion-inpainting` | Hugging Face 模型 ID |
| `INPAINT_SIZE` | `1024` | 修复区域的目标大小（像素） |
| `INPAINT_STEPS` | `50` | 扩散步数（越高质量越好但越慢） |
| `INPAINT_STRENGTH` | `1.0` | 修复强度 (0.0-1.0) |
| `INPAINT_PADDING` | `96` | 遮罩区域扩展像素数 |
| `INPAINT_MAX_REGIONS` | `32` | 最多修复多少个区域 |
| `HF_HOME` | `/data/hf-cache` | Hugging Face 模型缓存目录 |

## 性能注意事项

### CPU vs GPU

| 环境 | 速度 | 内存 | 推荐 |
|-----|-----|------|------|
| **GPU (NVIDIA)** | 5-10 秒/张 | ~6GB VRAM | ✅ **推荐** |
| **CPU** | 2-10 分钟/张 | ~8GB RAM | ❌ 不推荐 |

### 优化建议

1. **降低推理步数** - 减少 `INPAINT_STEPS` 来加速
   ```dockerfile
   ENV INPAINT_STEPS=25  # 更快，质量稍低
   ```

2. **降低分辨率** - 减少 `INPAINT_SIZE`
   ```dockerfile
   ENV INPAINT_SIZE=512  # 更快，细节可能丧失
   ```

3. **使用 GPU** - 使用 `Dockerfile.gpu` 替代
   ```bash
   docker build -f Dockerfile.gpu -t inpaint-service .
   docker run --gpus all -p 8002:8002 inpaint-service
   ```

## Docker 部署

### CPU 版本

```bash
docker build -f Dockerfile -t inpaint-service:cpu .
docker run -p 8002:8002 \
  -e INPAINT_STEPS=25 \
  -e INPAINT_SIZE=512 \
  inpaint-service:cpu
```

### GPU 版本（推荐）

```bash
docker build -f Dockerfile.gpu -t inpaint-service:gpu .
docker run --gpus all -p 8002:8002 \
  -v hf-cache:/data/hf-cache \
  inpaint-service:gpu
```

## Docker Compose

在 `docker-compose.yml` 中已配置：

```yaml
inpaint-service:
  build: ./inpaint-service
  expose:
    - "8002"
  environment:
    - INPAINT_SIZE=512
    - INPAINT_STEPS=50
    - HF_HOME=/data/hf-cache
  volumes:
    - hf-cache:/data/hf-cache
```

### 使用 Docker Compose 启动完整系统

#### CPU 版本（默认）

```bash
# 使用默认配置（使用 Dockerfile，CPU 版本）
docker-compose up -d

# 查看日志
docker-compose logs -f inpaint-service

# 验证服务
curl http://localhost:8002/health

# 停止所有服务
docker-compose down
```

#### GPU 版本（推荐用于生产）

**前提条件**：
- 安装 NVIDIA GPU
- 安装 NVIDIA Container Toolkit
- Docker 守护进程配置了 NVIDIA 运行时

**验证 GPU 支持**：
```bash
# 检查 NVIDIA Container Toolkit 是否安装
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi
```

**方法 1：使用 docker-compose.gpu.yml（推荐）**

```bash
# 启动 GPU 版本（需要创建/更新 docker-compose.gpu.yml）
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# 或只使用 GPU compose 文件（如果只部署 inpaint-service）
docker-compose -f docker-compose.gpu.yml up -d

# 查看日志
docker-compose -f docker-compose.gpu.yml logs -f inpaint-service

# 验证服务
curl http://localhost:8002/health

# 停止服务
docker-compose -f docker-compose.gpu.yml down
```

**方法 2：修改 docker-compose.yml 选择 GPU**

编辑 `docker-compose.yml`，修改 inpaint-service：

```yaml
inpaint-service:
  build:
    context: ./inpaint-service
    dockerfile: Dockerfile.gpu    # ← 改为 GPU 版本
  expose:
    - "8002"
  environment:
    - INPAINT_SIZE=1024          # ← GPU 可以用更大分辨率
    - INPAINT_STEPS=50
    - HF_HOME=/data/hf-cache
  volumes:
    - hf-cache:/data/hf-cache
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

然后启动：
```bash
docker-compose up -d --build
```

#### 最佳实践：创建独立的 GPU 配置文件

创建 `docker-compose.gpu.yml`（完整版本）：

```yaml
# docker-compose.gpu.yml - GPU 版本覆盖配置
version: '3.8'

services:
  inpaint-service:
    build:
      context: ./inpaint-service
      dockerfile: Dockerfile.gpu
    expose:
      - "8002"
    environment:
      - INPAINT_SIZE=1024          # GPU 可以处理更大分辨率
      - INPAINT_STEPS=50           # 保持高质量
      - INPAINT_STRENGTH=1.0
      - INPAINT_PADDING=96
      - HF_HOME=/data/hf-cache
    volumes:
      - hf-cache:/data/hf-cache
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia       # NVIDIA GPU
              device_ids: ['0']    # 使用 GPU 0（修改为实际 GPU ID）
              count: 1
              capabilities: [gpu]

volumes:
  hf-cache:
```

启动：
```bash
# 启动 GPU 版本
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# 查看 GPU 使用情况
docker stats
```

#### 对比：CPU vs GPU 配置

| 特性 | CPU 版本 | GPU 版本 |
|------|---------|---------|
| Dockerfile | `Dockerfile` | `Dockerfile.gpu` |
| INPAINT_SIZE | 512 (推荐) | 1024 |
| INPAINT_STEPS | 25-50 | 50+ |
| 推理速度 | 2-10 分钟/张 | 5-10 秒/张 |
| 启动时间 | 5-15 分钟 | 1-3 分钟 |
| GPU 驱动 | 不需要 | ✅ 需要 NVIDIA Container Toolkit |

#### 性能对比示例

```bash
# CPU 运行
docker-compose up -d
time curl -X POST http://localhost:8002/inpaint \
  -F "image=@test.png" \
  -F "mask=@mask.png" \
  -o output.png
# 预计时间: 2-10 分钟

# GPU 运行
docker-compose -f docker-compose.gpu.yml up -d
time curl -X POST http://localhost:8002/inpaint \
  -F "image=@test.png" \
  -F "mask=@mask.png" \
  -o output.png
# 预计时间: 5-10 秒 (100-120 倍加速)
```

### 现有 docker-compose.yml 说明

### 使用 Podman Compose 启动完整系统

Podman 是 Docker 的无守护进程替代品。使用 Podman Compose 命令基本相同：

#### 1. 安装 Podman Compose（如未安装）

```bash
# Windows (使用 scoop 或 choco)
scoop install podman-compose
# 或
choco install podman-compose

# Linux
sudo curl -o /usr/local/bin/podman-compose \
  https://raw.githubusercontent.com/containers/podman-compose/main/podman-compose
sudo chmod +x /usr/local/bin/podman-compose

# macOS
brew install podman-compose
```

#### 2. CPU 版本启动

```bash
# 使用 podman-compose 命令
podman-compose up -d

# 查看所有服务日志
podman-compose logs -f

# 仅查看 inpaint-service 日志
podman-compose logs -f inpaint-service

# 停止所有服务（保留数据）
podman-compose down

# 停止并删除所有内容
podman-compose down -v
```

#### 3. GPU 版本启动

```bash
# 检查 GPU 可用性
podman run --rm nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi

# 启动 GPU 版本（使用覆盖配置）
podman-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# 查看日志
podman-compose -f docker-compose.gpu.yml logs -f inpaint-service

# 停止
podman-compose -f docker-compose.gpu.yml down
```

#### 4. 常用 Podman Compose 命令

```bash
# 查看服务状态
podman-compose ps

# 启动指定服务
podman-compose up -d inpaint-service

# 重启服务
podman-compose restart inpaint-service

# 重建镜像
podman-compose build --no-cache

# 执行命令进入容器
podman-compose exec inpaint-service bash

# 查看容器资源使用
podman stats
```

### Docker Compose vs Podman Compose 对比

| 命令 | Docker | Podman |
|------|--------|--------|
| 启动服务 | `docker-compose up -d` | `podman-compose up -d` |
| 查看日志 | `docker-compose logs -f` | `podman-compose logs -f` |
| 停止服务 | `docker-compose down` | `podman-compose down` |
| 重建容器 | `docker-compose build --no-cache` | `podman-compose build --no-cache` |
| 查看状态 | `docker-compose ps` | `podman-compose ps` |

### Podman 特定配置

如果使用 Podman 遇到问题，可以创建 `.env` 文件来配置：

```env
# .env
COMPOSE_PODMAN_VERSION=4.0
PODMAN_USERNS=keep-id
```

### GPU 支持 (Podman)

在 Podman 中使用 GPU 需要额外配置：

```bash
# 检查 GPU 可用性
podman run --rm nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi

# 启动时指定 GPU
podman-compose -f docker-compose.gpu.yml up -d
```

如果使用 `docker-compose.gpu.yml`，确保修改 inpaint-service 为 GPU 版本：

```yaml
inpaint-service:
  build:
    context: ./inpaint-service
    dockerfile: Dockerfile.gpu
  device: ['nvidia.com/gpu=all']
```

### 常见问题

#### 文件权限错误

**错误**: `Permission denied` 或 `Cannot write to volume`

**解决**:
```bash
# 使用 rootless 模式
podman-compose run --user $(id -u):$(id -g) -v $(pwd):/app inpaint-service

# 或调整权限
podman run --rm -v $(pwd):/app alpine chmod 777 /app
```

#### 网络连接问题

**错误**: `Cannot reach ocr-service:8001`

**解决**:
```bash
# 检查网络
podman network ls
podman network inspect $(podman network ls -f name=pdf2pptx -q)

# 重建网络
podman-compose down --remove-orphans
podman network prune
podman-compose up -d
```

#### 模型下载失败

**现象**: 容器一直重启或日志显示网络超时

**解决**:
```bash
# 预先拉取模型
podman run --rm -v hf-cache:/data/hf-cache \
  python:3.10 bash -c \
  "pip install diffusers transformers && \
   python -c 'from diffusers import StableDiffusionInpaintPipeline; \
   StableDiffusionInpaintPipeline.from_pretrained(\"runwayml/stable-diffusion-inpainting\", \
   cache_dir=\"/data/hf-cache\")'"

# 然后启动服务
podman-compose up -d
```

## 调试

### 健康检查

```bash
curl http://localhost:8002/health
```

### 查看日志

```bash
docker logs <container_id>
```

日志会显示：
- 设备信息（GPU/CPU）
- 模型加载状态
- 每个修复请求的处理详情
- 任何错误信息

### 常见问题

#### 模型下载失败

**原因：** 网络问题或 Hugging Face API 限制  
**解决：** 
- 检查网络连接
- 预先下载模型：
  ```bash
  python -c "from diffusers import StableDiffusionInpaintPipeline; StableDiffusionInpaintPipeline.from_pretrained('runwayml/stable-diffusion-inpainting')"
  ```

#### 服务启动很慢

**原因：** 
- 首次运行需下载 ~5GB 模型
- 在 CPU 上运行

**解决：**
- 耐心等待首次启动（5-15 分钟）
- 使用 GPU 加速：切换到 `Dockerfile.gpu`

#### 内存不足（OOM）

**原因：**
- CPU 上运行大分辨率
- 同时处理多个请求

**解决：**
- 降低 `INPAINT_SIZE`
- 添加内存限制和自动重启：
  ```yaml
  inpaint-service:
    deploy:
      resources:
        limits:
          memory: 8G
    restart_policy:
      condition: on-failure
      max_attempts: 3
  ```

## 版本历史

### v0.2.0
- ✅ 添加详细日志记录
- ✅ 改进模型加载错误处理
- ✅ 优化 PyTorch 版本管理
- ✅ 增强 `/health` 端点
- ✅ 改进 Dockerfile 依赖安装
- ✅ 处理修复失败时的优雅降级

### v0.1.0
- 初始版本

## 许可证

与 pdf2pptx 项目相同。
