# 不用 Docker 启动 venus-4s

如果你不想装 Docker Desktop，就得自己在本机准备好 **MySQL 8** 和 **Redis 7+**。装完之后 `start-dev.bat` 会自动检测（脚本发现 docker 没跑就会走"本机服务"分支）。

---

## 一、装 MySQL 8

### 1. 下载安装

去 <https://dev.mysql.com/downloads/installer/> 下载 **MySQL Installer for Windows**（选带 MSI 那个，约 400MB 完整包）。

安装向导里：
- Setup Type 选 **Server only** 或 **Custom**（只勾 MySQL Server）
- Config Type 选 **Development Computer**
- Port：**3306**（默认，别改）
- Authentication Method 选 **Use Legacy Authentication Method**（重要，项目 compose 里也是这个）
- 设 root 密码：随便（比如 `devroot`），记住
- 勾选 **Start the MySQL Server at System Startup**（开机自启，省得每次手启）

### 2. 建库和账号

装完后开 cmd（管理员）：

```cmd
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```

输 root 密码进入 MySQL shell，然后：

```sql
CREATE DATABASE venus CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'venus'@'localhost' IDENTIFIED WITH mysql_native_password BY 'devpass';
GRANT ALL PRIVILEGES ON venus.* TO 'venus'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**账号/密码/库名必须完全一致**（`venus` / `devpass` / `venus`），因为 `config/dev.env` 里就是这么配的。

### 3. 验证

```cmd
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u venus -pdevpass -h 127.0.0.1 venus -e "SELECT 1;"
```

看到 `+---+ | 1 | +---+ | 1 | +---+` 就成功。

---

## 二、装 Redis 7

Windows 官方没有 Redis，用下面两个之一：

### 方案 A：Memurai（推荐，Windows 原生 Redis 兼容服务）

去 <https://www.memurai.com/get-memurai>，下 Developer Edition（免费），MSI 装完自动作为 Windows 服务开机自启，默认监听 `localhost:6379`。装完不用配。

### 方案 B：微软放的 Redis-for-Windows 老版本

<https://github.com/microsoftarchive/redis/releases> 下 `Redis-x64-3.2.100.msi`，MSI 装完也会注册成服务。**版本旧（3.2）**，但项目用到的命令（`SETEX / GET / DEL / EXISTS / INCR`）它都支持，够用。

### 验证

```cmd
redis-cli ping
```

返回 `PONG` 就 OK。

如果 `redis-cli` 不在 PATH，Memurai 装在 `C:\Program Files\Memurai\`，把这个目录加进 PATH 或者直接 `"C:\Program Files\Memurai\memurai-cli.exe" ping`。

---

## 三、启动项目

**关掉 Docker Desktop**（如果开着，脚本会优先走 Docker 分支），然后双击 `start-dev.bat`。脚本会：

1. 检测到 docker 没在跑 → 走本机分支
2. 从 `config/dev.env` 解析出 `localhost:3306` 和 `localhost:6379` → TCP 探测能通
3. `poetry install` 装后端依赖
4. `alembic upgrade head` 建表（首次会创建 `users` / `photos` / `analysis_tasks` / `reports` / `bookings` / `audit_logs` 等表）
5. `pnpm install` 装前端依赖
6. 两个新 cmd 分别起 API (8000) 和 Web (5173)

浏览器打开 <http://localhost:5173/> 应自动跳到 `/login`。

---

## 四、关闭

- API / Web：关掉两个 cmd 窗口即可
- MySQL / Redis：作为 Windows 服务在后台跑，不用管；开机会自启

如果不想让它们开机启动，`Win+R → services.msc`，找到 `MySQL80` 和 `Memurai`（或 `Redis`）把启动类型改成"手动"。

---

## 五、常见问题

**Q: 脚本报 `[X] MySQL localhost:3306 不可连接`**
- 打开 `services.msc` 看 `MySQL80` 服务是否在"正在运行"，没在跑就右键"启动"
- 装的是别的端口？改 `config/dev.env` 的 `DATABASE_URL` 里那个 `3306`

**Q: 脚本能过 MySQL 探测但 `alembic upgrade head` 失败**
- 大概率是账号/密码/库名对不上。回到"一、2. 建库和账号"重来一遍
- 或者看 `config/dev.env` 的 `DATABASE_URL` 跟你 SQL 里创建的账号是否完全一致

**Q: 想用本机已有的、非默认端口/账号的 MySQL**
- 改 `config/dev.env` 的 `DATABASE_URL`：
  ```
  DATABASE_URL=mysql+aiomysql://<你的用户>:<你的密码>@<host>:<port>/<db名>
  ```
- Redis 同理改 `REDIS_URL`

**Q: 每次电脑重启都要手动开 MySQL/Redis？**
- 装的时候勾了"开机自启"就不用；没勾的话去 `services.msc` 把它俩启动类型改成"自动"

**Q: 想彻底卸载 MySQL/Redis**
- MySQL：控制面板卸载 `MySQL Server 8.0` + 删 `C:\ProgramData\MySQL\`（存数据的地方）
- Memurai：控制面板卸载即可
