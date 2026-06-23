from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage
import time
print("本地GMT时间：", time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()))
# -------------------------- 配置API参数 --------------------------
# 从讯飞开放平台获取的密钥信息（请替换为你自己的）
SPARKAI_URL ="wss://spark-api.xf-yun.com/v3.1/chat"  # Spark Pro对应URL
SPARKAI_APP_ID ="9fae78ee"
SPARKAI_API_SECRET ="YTg5ZGUzZmI4ZjljNTAzOTc4OTQxNWYy"
SPARKAI_API_KEY ="ba9c324202671ff4069dab17d17f5d22"
SPARKAI_DOMAIN ="generalv3"  # Spark Pro对应domain参数
 
if __name__ == '__main__':
    # 1. 初始化星火大模型客户端
    spark = ChatSparkLLM(
        spark_api_url=SPARKAI_URL,
        spark_app_id=SPARKAI_APP_ID,
        spark_api_key=SPARKAI_API_KEY,
        spark_api_secret=SPARKAI_API_SECRET,
        spark_llm_domain=SPARKAI_DOMAIN,
        streaming=False,  # 关闭流式输出，一次性获取完整回复
    )
 
    # 2. 构建对话消息
    messages = [
        ChatMessage(
            role='user',  # 角色为用户
            content='你知道北京大学吗？'  # 用户提问内容
        )
    ]
 
    # 3. 创建回调处理器（可选，用于打印流式输出）
    handler = ChunkPrintHandler()
 
    # 4. 发起API调用
    a = spark.generate([messages], callbacks=[handler])
 
    # 5. 解析并打印模型回复
    answer = a.generations[0][0].text
    print("模型回答：")
    print(answer)