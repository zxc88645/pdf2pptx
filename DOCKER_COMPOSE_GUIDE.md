# Docker Compose 快速参考：CPU vs GPU

## 🚀 快速启动

### CPU 版本（默认）
```bash
# 启动
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f inpaint-service

# 停止
docker-compose down
```

### GPU 版本（NVIDIA 加速）
```bash
# 检查 GPU 驱动
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi

# 启动（方式 1：使用两个配置文件）
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# 启动（方式 2：仅启动 inpaint-service GPU 版本）
docker-compose -f docker-compose.gpu.yml up -d

# 查看日志
docker-compose -f docker-compose.gpu.yml logs -f inpaint-service

# 验证 GPU 使用
docker stats

# 停止
docker-compose -f docker-compose.gpu.yml down
```

---

## 📊 性能对比

### 推理时间（单张图像）

| 分辨率 | CPU | GPU (RTX 3090) | 加速倍数 |
|--------|-----|----------------|---------|
| 512×512 | 3-5 分钟 | 2-3 秒 | **60-150×** |
| 1024×1024 | 10-15 分钟 | 5-10 秒 | **100-180×** |

### 配置对比

| 配置项 | CPU 版本 | GPU 版本 |
|--------|---------|---------|
| **ocr-service** | `Dockerfile`（CPU） | `Dockerfile.gpu`（PaddlePaddle GPU） |
| **inpaint-service** | `Dockerfile`（CPU） | `Dockerfile.gpu`（CUDA PyTorch） |
| **INPAINT_SIZE** | 512 | 1024 |
| **INPAINT_STEPS** | 25-50 | 50-100 |
| **推理速度** | 2-15 分钟/张 | 2-10 秒/张 |
| **启动时间** | 5-15 分钟 | 1-3 分钟 |
| **内存需求** | RAM 8GB+ | VRAM 6GB+ |
| **驱动需求** | 无 | NVIDIA Container Toolkit |

---

## 📋 文件说明

### docker-compose.yml（CPU 版本）
- **用途**：开发、测试、无 GPU 环境
- **inpaint-service Dockerfile**：`Dockerfile`（CPU PyTorch）
- **分辨率**：512×512
- **推理步数**：50
- **速度**：较慢（2-15 分钟/张）

### docker-compose.gpu.yml（GPU 版本）
- **用途**：生产、高性能场景
- **ocr-service Dockerfile**：`Dockerfile.gpu`（PaddlePaddle GPU）
- **inpaint-service Dockerfile**：`Dockerfile.gpu`（GPU PyTorch）
- **分辨率**：1024×1024（更高质量）
- **推理步数**：50（保持高质量）
- **速度**：OCR 与 Inpaint 皆加速（5-10 秒/张）

---

## 🔧 使用场景选择

### 选择 CPU 版本（docker-compose.yml）当：
- ✅ 开发或测试环境
- ✅ 没有 NVIDIA GPU
- ✅ 对性能要求不高
- ✅ 需要最小化依赖

### 选择 GPU 版本（docker-compose.gpu.yml）当：
- ✅ 生产环境
- ✅ 需要快速处理大量 PDF
- ✅ 有 NVIDIA GPU 并安装了驱动
- ✅ 用户体验要求高（快速响应）

---

## ⚙️ GPU 环境配置

### 1. 检查 NVIDIA 驱动

```bash
# 查看驱动版本
nvidia-smi

# 查看 CUDA 版本
nvidia-smi | grep "CUDA Version"

# 如果未安装驱动，访问：
# https://www.nvidia.com/Download/driverDetails.aspx
```

### 2. 安装 NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 验证安装
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi
```

### 3. 验证 Docker GPU 支持

```bash
# 应该输出 GPU 信息
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi
```

---

## 💡 优化建议

### 对于 CPU 环境
```bash
# 1. 降低分辨率加速
export INPAINT_SIZE=256

# 2. 减少推理步数
export INPAINT_STEPS=20

# 3. 启动
docker-compose up -d
```

### 对于 GPU 环境
```bash
# 1. 提高分辨率获得更好质量
export INPAINT_SIZE=1536

# 2. 增加推理步数提升质量
export INPAINT_STEPS=75

# 3. 启动
docker-compose -f docker-compose.gpu.yml up -d
```

### 多 GPU 支持（如果有多个 GPU）

编辑 `docker-compose.gpu.yml`：

```yaml
inpaint-service:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 2              # 使用 2 个 GPU
            capabilities: [gpu]
          # 或指定具体 GPU ID:
          # device_ids: ['0', '1']
```

---

## 🐛 故障排查

### GPU 无法识别

**错误**：`could not select device driver "" with capabilities: [[gpu]]`

**解决**：
```bash
# 重新安装 NVIDIA Container Toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 验证
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi
```

### 内存溢出（OOM）

**错误**：`CUDA out of memory`

**解决**：
```bash
# 降低分辨率
export INPAINT_SIZE=512

# 或减少推理步数
export INPAINT_STEPS=25

# 重启
docker-compose -f docker-compose.gpu.yml up -d
```

### 模型下载超时

**现象**：容器反复重启

**解决**：
```bash
# 手动预缓存模型
docker run --rm \
  -v hf-cache:/data/hf-cache \
  -e HF_HOME=/data/hf-cache \
  pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime \
  python -c "from diffusers import StableDiffusionInpaintPipeline; \
             StableDiffusionInpaintPipeline.from_pretrained('runwayml/stable-diffusion-inpainting')"

# 然后启动 GPU 版本
docker-compose -f docker-compose.gpu.yml up -d
```

---

## 📈 性能监控

### 实时监控

```bash
# 查看容器 CPU/内存/GPU 用量
docker stats

# 仅监控 inpaint-service
docker stats pdf2pptx-inpaint-service-1

# 监控 GPU 用量
watch -n 1 nvidia-smi
```

### 查看详细日志

```bash
# 显示最近 100 行日志
docker-compose logs -f --tail=100 inpaint-service

# 查看特定时间范围
docker-compose logs --since 2024-01-01T10:00:00 inpaint-service
```

---

## 🔄 从 CPU 切换到 GPU（反之亦然）

### CPU → GPU

```bash
# 1. 停止 CPU 版本
docker-compose down

# 2. 清理 CPU 容器和镜像（可选）
docker-compose down -v --rmi all

# 3. 启动 GPU 版本
docker-compose -f docker-compose.gpu.yml up -d
```

### GPU → CPU

```bash
# 1. 停止 GPU 版本
docker-compose -f docker-compose.gpu.yml down

# 2. 启动 CPU 版本
docker-compose up -d
```

---

## 📚 参考资源

- [NVIDIA Container Toolkit 文档](https://github.com/NVIDIA/nvidia-docker)
- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [PyTorch CUDA 说明](https://pytorch.org/get-started/locally/)
- [Stable Diffusion 官方文档](https://huggingface.co/runwayml/stable-diffusion-inpainting)

---

## ✅ 检查清单

启动前请确认：

- [ ] 网络连接正常
- [ ] Docker/Podman 已安装并运行
- [ ] **GPU 版本**：安装了 NVIDIA Container Toolkit
- [ ] **GPU 版本**：`nvidia-smi` 可以识别 GPU
- [ ] 有足够的磁盘空间（~10GB 用于模型）
- [ ] 端口 8000, 5173, 8001, 8002 未被占用

完成以上检查后，即可运行相应版本！
