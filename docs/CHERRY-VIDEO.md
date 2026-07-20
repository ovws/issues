# Cherry Studio 使用 Grok 视频

本项目在 Grok 网关的 OpenAI `chat/completions` 接口上提供视频兼容桥接。普通同事不需要调用 Swagger、编写脚本或手动轮询视频任务。

## 服务商配置

在 Cherry Studio 的“设置 → 模型服务 → 添加”中填写：

```text
服务商类型：OpenAI
名称：Grok 内网
API 地址：http://<服务器内网 IP>:8001/v1
API Key：管理员分配的个人 sk-internal-... 密钥
```

手动添加模型：

```text
模型 ID：grok-imagine-video-1.5
模型名称：Grok 视频
模型类型：对话模型
```

开启服务商开关。连通性检查不会生成视频；未提供图片时，接口只会返回上传图片的提示。

## 生成视频

1. 在 Cherry Studio 新建对话并选择“Grok 视频”。
2. 上传一张 JPG、PNG、WebP 或 GIF 图片。
3. 输入希望画面如何运动，例如“让人物缓慢转头，镜头平滑推进，电影感”。
4. 发送消息并等待生成完成。
5. 助手会返回可直接播放或下载的视频链接。

默认参数为 5 秒、720p、16:9。当前 `grok-imagine-video-1.5` 必须提供首图，不支持纯文字生成视频。

生成请求仍需个人 API Key，并进入 Grok 独立 FIFO 队列。完成链接使用不可猜测的任务 ID，拿到链接的人可以直接访问成品，因此不要把链接转发给无关人员。

