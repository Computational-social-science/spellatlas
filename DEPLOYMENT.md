# 生产环境部署与优化指南 (Deployment & Optimization Guide)

本指南旨在帮助您将 SpellAtlas 从开发环境迁移到生产环境（如 Render, Fly.io, Vercel），并进行关键的架构优化。

## 1. 数据库连接池 (Database Connection Pooling)

在生产环境（特别是使用 Supabase 等托管数据库时），频繁创建和销毁数据库连接会导致性能瓶颈甚至耗尽连接数。我们已经在后端实现了连接池。

### 实现细节
- **代码位置**: `backend/storage.py`
- **机制**: 使用 `psycopg2.pool.ThreadedConnectionPool`。
- **配置**:
  - `minconn=1`: 最小保持1个连接。
  - `maxconn=20`: 最大允许20个连接（适应免费层限制）。
- **用法**:
  ```python
  # 使用上下文管理器自动获取和归还连接
  with self.get_connection() as conn:
      cursor = conn.cursor()
      # 执行查询...
  ```

## 2. 实时性与 WebSocket (Real-time Updates)

为了向前端实时推送新检测到的错误，我们集成了 FastAPI WebSocket。

### 优化点
- **心跳机制 (Heartbeat)**: 每5秒发送一次心跳，防止负载均衡器（Load Balancer）因连接空闲而切断连接。
- **断线重连**: 前端 `GameController.svelte` 已包含自动重连逻辑。
- **模拟模式**: 当数据库为空时，后端自动切换到模拟模式，发送随机数据以供展示。

## 3. 异步任务队列 (Async Task Queue)

数据密集型任务（如抓取新闻、NLP分析）不应阻塞主 API 线程。我们采用了 **FastAPI BackgroundTasks** + **Subprocess** 模式。

### 架构
- **触发端点**: `POST /api/trigger-pipeline`
- **执行流程**:
  1. API 立即返回 `202 Accepted`。
  2. 后台启动子进程运行 `backend.fetch_news`。
  3. 完成后，启动子进程运行 `backend.detect_errors`。
  4. 最后，热重载内存中的数据存储 (`storage.load_data()`)。

这种方式实现了任务的异步执行和进程隔离，避免了复杂的 Celery/Redis 依赖，非常适合中小型项目。

## 4. 部署检查清单 (Deployment Checklist)

### A. 数据库 (Supabase)
1. [ ] 创建 Supabase 项目。
2. [ ] 获取 Connection String (URI 模式)。
3. [ ] 在 Render 环境变量中设置 `DATABASE_URL`。

### B. 后端 (Render)
1. [ ] **Build Command**: `pip install -r backend/requirements.txt`
2. [ ] **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. [ ] **Environment Variables**:
   - `PYTHON_VERSION`: `3.11.0`
   - `DATABASE_URL`: `postgresql://...`
   - `ALLOWED_ORIGINS`: `https://your-frontend.vercel.app`

### C. 前端 (Vercel)
1. [ ] **Framework Preset**: Vite
2. [ ] **Build Command**: `npm run build`
3. [ ] **Output Directory**: `dist`
4. [ ] **Environment Variables**:
   - `VITE_API_URL`: `https://your-backend.onrender.com`
   - `VITE_WS_URL`: `wss://your-backend.onrender.com/ws`

## 5. 本地端到端测试 (Local End-to-End Testing)

使用 Docker Compose 在本地模拟生产环境。

```bash
# 构建并启动服务
docker-compose up --build

# 访问前端
http://localhost:5173

# 访问后端 API 文档
http://localhost:8000/docs
```

## 6. 备份与恢复 (Backup & Recovery)

- **Supabase**: 每日自动备份（取决于套餐，免费版通常保留7天）。
- **手动备份**:
  ```bash
  pg_dump "your-connection-string" > backup.sql
  ```
- **数据恢复**:
  ```bash
  psql "your-connection-string" < backup.sql
  ```

---

**下一步**: 按照上述清单配置环境变量，并推送到 GitHub 触发部署。
