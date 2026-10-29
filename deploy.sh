#!/bin/bash
# ==============================================
#  直播中控台 - Ubuntu 一键部署脚本
#  使用方法:
#    chmod +x deploy.sh
#    ./deploy.sh
# ==============================================

set -e
echo "========================================"
echo " Live Stream DB - Deploy to Ubuntu"
echo "========================================"

APP_DIR="/opt/live_stream_db"
APP_USER="livedb"
SERVICE_NAME="live-stream-db"

# 1. 更新系统 & 安装 Python3
echo "[1/6] Installing dependencies..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv nginx

# 2. 创建运行用户
echo "[2/6] Creating user $APP_USER..."
if ! id "$APP_USER" &>/dev/null; then
    sudo useradd -r -s /bin/false "$APP_USER"
fi

# 3. 复制项目
echo "[3/6] Copying project to $APP_DIR..."
sudo mkdir -p "$APP_DIR"
sudo cp -r . "$APP_DIR"
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# 4. 创建虚拟环境 & 安装依赖
echo "[4/6] Setting up Python venv..."
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt

# 5. 创建 systemd 服务
echo "[5/6] Creating systemd service..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Live Stream Control Panel
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/wsgi.py
Restart=always
RestartSec=5
Environment=LIVE_DB_PASSWORD=

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# 6. 配置 Nginx（可选，如果需要 80 端口）
echo "[6/6] Setting up Nginx..."
sudo tee /etc/nginx/sites-available/live-stream-db > /dev/null <<'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/live-stream-db /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "========================================"
echo "  Deploy Complete!"
echo "  Access: http://$(curl -s ifconfig.me)"
echo "========================================"
echo ""
echo "  Commands:"
echo "    sudo systemctl status $SERVICE_NAME"
echo "    sudo systemctl restart $SERVICE_NAME"
echo "    sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "  Set password:"
echo "    sudo sed -i 's/LIVE_DB_PASSWORD=/LIVE_DB_PASSWORD=你的密码/' /etc/systemd/system/${SERVICE_NAME}.service"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl restart $SERVICE_NAME"
echo ""
