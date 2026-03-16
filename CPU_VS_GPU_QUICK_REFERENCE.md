# Docker Compose CPU vs GPU - 快速参考

## 一句话总结

- **CPU**: `docker-compose up -d` （开发/测试，慢）
- **GPU**: `docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` （生产/快速，需要 NVIDIA 驱动）

---

## 🚀 启动命令

### CPU 版本
```bash
# 启动
docker-compose up -d

# 停止
docker-compose down
```

### GPU 版本
```bash
# 启动（方式 1：推荐，结合两个配置文件）
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# 启动（方式 2：仅启动 inpaint-service）
docker-compose -f docker-compose.gpu.yml up -d

# 停止
docker-compose -f docker-compose.gpu.yml down
```

### Podman 版本同样适用
```bash
# CPU
podman-compose up -d

# GPU
podman-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

---

## 📈 性能对比

| 指标 | CPU | GPU |
|-----|-----|-----|
| **推理速度** | 2-15 分钟/张 | 5-10 秒/张 |
| **加速倍数** | 基准 | **100-180 倍** |
| **分辨率** | 512×512 | 1024×1024 |
| **启动时间** | 5-15 分钟 | 1-3 分钟 |
| **推介步数** | 25-50 | 50+ |

### 实际例子：处理 10 页 PDF

**CPU 模式**
- 推理时间：10 × 5 分钟 = 50 分钟
- 总耗时：约 1 小时

**GPU 模式**
- 推理时间：10 × 5 秒 = 50 秒
- 总耗时：约 2 分钟

📊 **GPU 快 30 倍**

---

## ✅ 前置条件检查

### 所有环境都需要
- [ ] Docker 或 Podman 已安装
- [ ] 网络连接正常
- [ ] 端口 8000, 5173, 8001, 8002 未被占用
- [ ] 磁盘空间 ≥ 10GB（用于模型缓存）

### GPU 环境额外需要
- [ ] NVIDIA 显卡
- [ ] NVIDIA 驱动已安装
  ```bash
  nvidia-smi  # 应该能看到 GPU 信息
  ```
- [ ] NVIDIA Container Toolkit 已安装
  ```bash
  docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi
  ```

---

## 🔧 配置文件对比

### docker-compose.yml（CPU）
```yaml
inpaint-service:
  build: ./inpaint-service
  # Dockerfile 会自动安装 PyTorch CPU 版本
  environment:
    - INPAINT_SIZE=512          # CPU: 较小分辨率
    - INPAINT_STEPS=50
```

### docker-compose.gpu.yml（GPU）
```yaml
inpaint-service:
  build:
    dockerfile: Dockerfile.gpu  # 使用 GPU Dockerfile
  environment:
    - INPAINT_SIZE=1024         # GPU: 更大分辨率
    - INPAINT_STEPS=50
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia      # 请求 GPU
            count: 1            # 使用 1 个 GPU
            capabilities: [gpu]
```

---

## 🎯 决策树

```
需要转换 PDF?
│
├─ Yes, 开发环境
│  └─ 使用 CPU 版本 ✅
│     docker-compose up -d
│
└─ Yes, 生产环境
   │
   ├─ 有 NVIDIA GPU？
   │  │
   │  ├─ Yes ─→ 使用 GPU 版本 ✅✅ (推荐)
   │  │        docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
   │  │
   │  └─ No ──→ 使用 CPU 版本 ✅
   │           docker-compose up -d
   │           （但会很慢）
   │
   └─ 对速度要求高？
      │
      ├─ Yes ──→ 买 GPU 或使用云服务 (如 AWS p3 实例)
      │
      └─ No ───→ CPU 版本可接受 ✅
```

---

## 📝 环境变量调优

### CPU 环境优化（加快速度）
```bash
export INPAINT_SIZE=256       # 降低分辨率
export INPAINT_STEPS=20       # 减少步数
docker-compose up -d
```

### GPU 环境优化（提升质量）
```bash
export INPAINT_SIZE=1536      # 提高分辨率
export INPAINT_STEPS=75       # 增加步数
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

---

## 🔄 从 CPU 切换到 GPU（或反过来）

### CPU → GPU
```bash
# 1. 停止并清理 CPU 版本
docker-compose down -v

# 2. 启动 GPU 版本
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

### GPU → CPU
```bash
# 1. 停止 GPU 版本
docker-compose -f docker-compose.gpu.yml down

# 2. 启动 CPU 版本
docker-compose up -d --build
```

**注意**：模型缓存保留在 volume 中，切换版本时无需重新下载

---

## 🐛 常见问题

### Q: GPU 无法识别
**A**: 检查 NVIDIA Container Toolkit
```bash
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi
# 应该显示 GPU 信息
```

### Q: CPU 版本太慢了
**A**: 有三个选择
1. 降低参数（见上面的优化部分）
2. 改用 GPU
3. 等待（2-15 分钟/张是正常的）

### Q: GPU 显存不足（OOM）
**A**: 降低分辨率或步数
```bash
export INPAINT_SIZE=512
export INPAINT_STEPS=25
docker-compose -f docker-compose.gpu.yml up -d
```

### Q: 模型下载失败
**A**: 网络问题，预先缓存模型
```bash
./scripts/download-models.ps1  # Windows
./scripts/download-models.sh   # Linux/macOS
```

---

## 📚 完整文档

- 详细 Docker Compose 指南：[DOCKER_COMPOSE_GUIDE.md](DOCKER_COMPOSE_GUIDE.md)
- Podman 专用指南：[PODMAN_GUIDE.md](PODMAN_GUIDE.md)
- Inpaint 服务文档：[inpaint-service/README.md](inpaint-service/README.md)

---

## 速查表（复制粘贴）

| 需求 | 命令 |
|------|------|
| CPU 启动 | `docker-compose up -d` |
| GPU 启动 | `docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` |
| CPU 停止 | `docker-compose down` |
| GPU 停止 | `docker-compose -f docker-compose.gpu.yml down` |
| 查看日志 | `docker-compose logs -f inpaint-service` |
| 查看状态 | `docker-compose ps` |
| 清理数据 | `docker-compose down -v` |
| 监控 GPU | `watch -n 1 nvidia-smi` |
| Podman 同上 | 将 `docker-compose` 改为 `podman-compose` |

---

**👉 立即开始**：[DOCKER_COMPOSE_GUIDE.md](DOCKER_COMPOSE_GUIDE.md)
