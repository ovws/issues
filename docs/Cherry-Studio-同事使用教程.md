# Cherry Studio 配置教程

## 1. 打开配置页面

打开 Cherry Studio，点击右上角 **设置（齿轮）** → **服务商 / Model Provider** → **添加 / Add**。

![image-20260721085607350](C:\Users\admin\AppData\Roaming\Typora\typora-user-images\image-20260721085607350.png)

![image-20260721085709808](C:\Users\admin\AppData\Roaming\Typora\typora-user-images\image-20260721085709808.png)

![image-20260721085927609](C:\Users\admin\AppData\Roaming\Typora\typora-user-images\image-20260721085927609.png)

![image-20260721090639047](C:\Users\admin\AppData\Roaming\Typora\typora-user-images\image-20260721090639047.png)

![image-20260721093856273](C:\Users\admin\AppData\Roaming\Typora\typora-user-images\image-20260721093856273.png)

![image-20260721090749176](C:\Users\admin\AppData\Roaming\Typora\typora-user-images\image-20260721090749176.png)

![image-20260721090903597](C:\Users\admin\AppData\Roaming\Typora\typora-user-images\image-20260721090903597.png)

## 2. 填写服务商信息

服务商类型选择：**OpenAI** 或 **OpenAI Compatible（OpenAI 兼容）**。

然后填写以下内容：

| 配置项 | 填写内容 |
|---|---|
| 名称 | 例如：`公司AI-Grok` |
| API Host / API 地址 | `http://公司内网IP:端口/v1` |
| API Key / 密钥 | 发给您的个人 API Key |
| 模型 | 点击“刷新模型”后选择管理员指定的模型 |

端口对应关系：

| 服务 | API 地址 |
|---|---|
| Grok | `https://grok.loser.dev/v1` |
| Gemini | `https://gemn.loser.dev/v1` |
| ChatGPT 图片 | `https://gpt5.loser.dev/v1` |

公网地址保持不变，由公司网关负责转发到各平台服务；不要让同事改成
`127.0.0.1` 或服务器内网地址。

## 3. 保存并测试

点击 **保存**，返回聊天页面，选择刚添加的服务商和模型，发送：

```text
你好，请回复“连接成功”。
```

能正常回复就配置完成。

## 常见问题

- **连接失败**：确认地址最后包含 `/v1`。
- **401 / Key 无效**：重新粘贴 API Key，注意不要带空格。
- **找不到模型**：点击刷新模型，或向管理员索要准确的模型名称。
- **图片不能用**：确认选择了支持图片的服务和模型。
- **视频模型报端点不兼容**：不要选原始模型 `grok-imagine-video-1.5`。在 `Me` 服务商中重新获取模型列表，改选 `grok-imagine-video-1.5-vision`；该兼容模型可在普通聊天中把最新图片转成视频。

不要把 `.env`、Cookie 或别人的 API Key 导入 Cherry Studio。
