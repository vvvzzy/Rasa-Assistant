# Rasa 点餐助手

## 1. 创建环境
```bat
conda env create -f environment.yml
conda activate rasa-order-bot
```

## 2. 训练模型
```bat
rasa train
```

## 3. 启动服务
打开 3 个 Anaconda Prompt，均进入项目目录并激活环境。

终端 1：
```bat
rasa run actions
```

终端 2：
```bat
rasa run --enable-api --cors "*"
```

终端 3：
```bat
python app.py
```

浏览器访问：http://127.0.0.1:8080

## 4. 第三方 API 对比
复制 `.env.example` 为 `.env`，填写图灵机器人 API Key，然后运行：
```bat
python scripts\compare_api.py
```

测试句：我要两份牛肉面
