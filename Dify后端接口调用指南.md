# Dify 后端接口调用指南

## 📋 目录

- [架构概述](#架构概述)
- [调用流程](#调用流程)
- [核心 API 端点](#核心-api-端点)
- [流式响应处理](#流式响应处理)
- [功能实现详解](#功能实现详解)
- [完整调用示例](#完整调用示例)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

---

## 架构概述

### 调用架构

```
前端 (Vue/UniApp)
    ↓
直接调用 (不经过后端)
    ↓
Dify API Server
    ↓
返回响应到前端
```

### 关键设计决策

- ✅ **前端直接调用**：不经过 PHP 后端，减少延迟
- ✅ **配置集中管理**：从 PHP 后端获取配置（token、baseUrl）
- ✅ **SSE 流式响应**：使用 Server-Sent Events 实现实时对话
- ✅ **跨域处理**：Dify API 需要配置 CORS

---

## 调用流程

### 1. 初始化配置

```typescript
// 步骤 1: 从后端获取配置
const appConfig = await getConfig() // 调用 /api/pc/config

// 步骤 2: 存储到 Pinia Store
difyStore.config = appConfig.dify

// 步骤 3: 验证配置
if (!difyStore.config.token || !difyStore.config.baseUrl) {
  throw new Error('Dify config not initialized')
}
```

### 2. 发送消息流程

```typescript
// 完整流程
async function sendMessage(query: string) {
  // 1. 获取配置
  const { token, baseUrl } = difyStore.config
  const userId = getUserId()

  // 2. 发送请求
  const response = await fetch(`${baseUrl}/v1/chat-messages`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: query,
      response_mode: 'streaming', // 流式响应
      user: userId,
      conversation_id: currentConversationId || undefined,
      inputs: {},
      files: uploadedFiles
    })
  })

  // 3. 获取响应流
  const stream = response.body

  // 4. 解析流式响应
  for await (const event of parseStream(stream)) {
    handleStreamEvent(event)
  }
}
```

---

## 核心 API 端点

### 1. 发送聊天消息

#### 端点

```
POST {baseUrl}/v1/chat-messages
```

#### 请求头

```typescript
{
  'Authorization': 'Bearer {token}',
  'Content-Type': 'application/json'
}
```

#### 请求体

```typescript
{
  // 必填
  query: string                    // 用户输入的文本
  response_mode: 'streaming'       // 响应模式：streaming 或 blocking

  // 可选
  user: string                     // 用户唯一标识
  conversation_id: string          // 对话 ID（首次对话不传）
  inputs: Record<string, any>      // 应用变量
  files: Array<{
    type: 'image' | 'document'     // 文件类型
    transfer_method: string        // 传输方式：local_file
    upload_file_id: string         // 上传后的文件 ID
  }>
}
```

#### 响应（流式）

```
data: {"event": "message", "answer": "你好"}
data: {"event": "message", "answer": "！"}
data: {"event": "message_end", "conversation_id": "xxx", "message_id": "yyy"}
data: [DONE]
```

#### 完整实现

```typescript
// 文件：/pc/api/dify.ts
export function sendMessage(params: SendMessageParams) {
  const config = useDifyStore().config
  const difyApiUrl = config.baseUrl.replace(/\/$/, '')

  return fetch(`${difyApiUrl}/v1/chat-messages`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${config.token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: params.query,
      response_mode: 'streaming',
      user: getUserId(),
      conversation_id: params.conversation_id || undefined,
      inputs: {},
      files: params.files
    })
  }).then(response => response.body)
}
```

---

### 2. 停止生成

#### 端点

```
POST {baseUrl}/v1/chat-messages/{task_id}/stop
```

#### 请求体

```typescript
{
  user: string  // 用户 ID
}
```

#### 实现

```typescript
export function stopResponse(taskId: string) {
  const config = useDifyStore().config
  const difyApiUrl = config.baseUrl.replace(/\/$/, '')

  return fetch(`${difyApiUrl}/v1/chat-messages/${taskId}/stop`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${config.token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ user: getUserId() })
  }).then(response => response.json())
}
```

---

### 3. 消息反馈

#### 端点

```
POST {baseUrl}/v1/messages/{message_id}/feedbacks
```

#### 请求体

```typescript
{
  rating: 'like' | 'dislike' | null,  // 点赞/点踩/取消
  user: string,                       // 用户 ID
  content: string | null              // 反馈内容（可选）
}
```

#### 实现

```typescript
export function feedbackMessage(
  messageId: string,
  rating: 'like' | 'dislike' | null,
  content?: string
) {
  const config = useDifyStore().config
  const difyApiUrl = config.baseUrl.replace(/\/$/, '')

  return fetch(`${difyApiUrl}/v1/messages/${messageId}/feedbacks`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${config.token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      rating,
      user: getUserId(),
      content: content || null
    })
  }).then(response => response.json())
}
```

---

### 4. 获取对话列表

#### 端点

```
GET {baseUrl}/v1/conversations
```

#### 查询参数

```
?user={userId}&limit=20&sort_by=-updated_at
```

#### 实现

```typescript
export function getConversations(limit = 20) {
  const config = useDifyStore().config
  const difyApiUrl = config.baseUrl.replace(/\/$/, '')

  const params = new URLSearchParams({
    user: getUserId(),
    limit: limit.toString(),
    sort_by: '-updated_at'
  })

  return fetch(`${difyApiUrl}/v1/conversations?${params}`, {
    headers: {
      'Authorization': `Bearer ${config.token}`
    }
  }).then(response => response.json())
}
```

---

### 5. 获取消息历史

#### 端点

```
GET {baseUrl}/v1/messages
```

#### 查询参数

```
?conversation_id={convId}&user={userId}&limit=50
```

#### 实现

```typescript
export function getMessages(conversationId: string, limit = 20) {
  const config = useDifyStore().config
  const difyApiUrl = config.baseUrl.replace(/\/$/, '')

  const params = new URLSearchParams({
    conversation_id: conversationId,
    user: getUserId(),
    limit: limit.toString()
  })

  return fetch(`${difyApiUrl}/v1/messages?${params}`, {
    headers: {
      'Authorization': `Bearer ${config.token}`
    }
  }).then(response => response.json())
}
```

---

### 6. 上传文件

#### 端点

```
POST {baseUrl}/v1/files/upload
```

#### 请求体（multipart/form-data）

```
file: {文件二进制数据}
user: {userId}
```

#### 实现

```typescript
export function uploadFile(file: File) {
  const config = useDifyStore().config
  const difyApiUrl = config.baseUrl.replace(/\/$/, '')

  const formData = new FormData()
  formData.append('file', file)
  formData.append('user', getUserId())

  return fetch(`${difyApiUrl}/v1/files/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${config.token}`
    },
    body: formData
  }).then(response => response.json())
  .then(result => {
    // 补充完整 URL
    if (result.source_url) {
      return {
        ...result,
        fullUrl: `${difyApiUrl}${result.source_url}`
      }
    }
    return result
  })
}
```

---

### 7. 文件预览

#### 端点

```
GET {baseUrl}/v1/files/{file_id}/preview
```

#### 查询参数

```
?as_attachment=true  // 下载文件
```

#### 实现

```typescript
export function getFilePreviewUrl(fileId: string): string {
  const config = useDifyStore().config
  const difyApiUrl = config.baseUrl.replace(/\/$/, '')
  return `${difyApiUrl}/v1/files/${fileId}/preview`
}

// 下载文件
export async function downloadFile(file: any) {
  const baseUrl = difyStore.config.baseUrl.replace(/\/$/, '')
  const downloadUrl = `${baseUrl}/v1/files/${file.id}/preview?as_attachment=true`

  const response = await fetch(downloadUrl, {
    headers: {
      'Authorization': `Bearer ${difyStore.config.token}`
    }
  })

  const blob = await response.blob()
  const blobUrl = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = blobUrl
  link.download = file.name
  link.click()

  URL.revokeObjectURL(blobUrl)
}
```

---

### 8. 语音转文字

#### 端点

```
POST {baseUrl}/v1/audio-to-text
```

#### 请求体（multipart/form-data）

```
file: {音频文件}
user: {userId}
```

#### 实现

```typescript
export async function audioToText(
  audioBlob: Blob,
  extension = 'webm'
): Promise<string> {
  const config = useDifyStore().config
  const difyApiUrl = config.baseUrl.replace(/\/$/, '')

  const fileName = `recording.${extension}`
  const formData = new FormData()
  formData.append('file', audioBlob, fileName)
  formData.append('user', getUserId())

  const response = await fetch(`${difyApiUrl}/v1/audio-to-text`, {
    method: 'POST',
    body: formData,
    headers: {
      'Authorization': `Bearer ${config.token}`
    }
  })

  const result = await response.json()
  return result.text
}
```

---

## 流式响应处理

### SSE 格式解析

```typescript
export async function* parseStream(body: ReadableStream): AsyncGenerator<any> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const MAX_BUFFER_SIZE = 10 * 1024 * 1024 // 10MB

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // 防止缓冲区溢出
    if (buffer.length > MAX_BUFFER_SIZE) {
      console.warn('[Stream] Buffer overflow, clearing...')
      buffer = buffer.slice(-MAX_BUFFER_SIZE / 2)
    }

    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6).trim()
        if (jsonStr && jsonStr !== '[DONE]') {
          try {
            yield JSON.parse(jsonStr)
          } catch (e) {
            console.error('[Stream] Parse error:', e)
          }
        }
      }
    }
  }
}
```

### 事件类型处理

```typescript
// 监听流式事件
for await (const event of parseStream(stream)) {
  switch (event.event) {
    case 'message':
      // 消息片段 - 更新 AI 回复
      updateMessageContent(event.answer)
      break

    case 'message_end':
      // 消息结束 - 保存对话 ID
      currentConversationId = event.conversation_id
      messageId = event.message_id
      taskCompleted()
      break

    case 'message_file':
      // 文件事件 - 显示附件
      showFileAttachment({
        id: event.id,
        type: event.type,
        url: event.url,
        belongs_to: event.belongs_to
      })
      break

    case 'message_replace':
      // 内容审查替换
      replaceMessageContent(event)
      break

    case 'workflow_started':
      // 工作流开始
      workflowStarted(event)
      break

    case 'node_started':
      // 节点开始
      nodeStarted(event)
      break

    case 'node_finished':
      // 节点结束 - 更新思考过程
      updateThinkingProcess(event)
      break

    case 'error':
      // 错误处理
      handleError(event)
      break

    case 'ping':
      // 保活事件 - 忽略
      break
  }
}
```

### 消息内容更新

```typescript
// 在 Store 中处理流式事件
async sendMessage(query: string, files?: any[]) {
  // 1. 添加用户消息
  this.messages.push({
    id: `user_${Date.now()}`,
    role: 'user',
    content: query,
    createdAt: new Date()
  })

  // 2. 添加空的助手消息
  const assistantMessage: DifyMessage = {
    id: `assistant_${Date.now()}`,
    role: 'assistant',
    content: '',
    createdAt: new Date(),
    nodeOutputs: {}
  }
  this.messages.push(assistantMessage)

  // 3. 开始流式响应
  this.isTyping = true
  this.currentTaskId = null

  try {
    const stream = await sendMessage({
      query,
      conversation_id: this.currentConversationId,
      files
    })

    // 4. 处理流式事件
    for await (const event of parseStream(stream)) {
      switch (event.event) {
        case 'message':
          // 累积消息内容
          assistantMessage.content += event.answer || ''
          break

        case 'message_end':
          // 保存对话 ID
          this.currentConversationId = event.conversation_id
          this.currentTaskId = null
          this.isTyping = false
          break

        case 'node_finished':
          // 保存节点输出（思考过程）
          if (event.node_type === 'llm') {
            assistantMessage.nodeOutputs[event.node_id] = {
              title: event.title,
              node_type: event.node_type,
              status: event.status,
              outputs: event.outputs,
              elapsedTime: event.metadata?.elapsed_time
            }
          }
          break

        case 'error':
          this.error = event.message
          this.isTyping = false
          break
      }
    }
  } catch (error) {
    this.error = error.message
    this.isTyping = false
  }
}
```

---

## 功能实现详解

### 1. 文件上传流程

```typescript
// 完整流程
async function handleFileUpload(file: File) {
  // 1. 上传文件到 Dify
  const result = await uploadFile(file)

  // 2. 构建文件引用
  const fileRef = {
    type: file.type.startsWith('image/') ? 'image' : 'document',
    transfer_method: 'local_file',
    upload_file_id: result.id
  }

  // 3. 发送消息时附加文件
  await sendMessage('请看这张图片', [fileRef])
}

// 上传函数
async function uploadFile(file: File) {
  const config = difyStore.config
  const formData = new FormData()
  formData.append('file', file)
  formData.append('user', getUserId())

  const response = await fetch(
    `${config.baseUrl}/v1/files/upload`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${config.token}` },
      body: formData
    }
  )

  return response.json() // { id, name, size, type, url }
}
```

### 2. 语音输入流程

```typescript
// 完整流程
async function voiceInput() {
  // 1. 录制音频
  const audioBlob = await recordAudio()

  // 2. 转换为 WAV 格式
  const wavBlob = await convertToWav(audioBlob)

  // 3. 语音转文字
  const text = await audioToText(wavBlob, 'wav')

  // 4. 填充到输入框
  inputQuery.value += text
}

// 录音函数
async function recordAudio(): Promise<Blob> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const mediaRecorder = new MediaRecorder(stream, {
    mimeType: 'audio/webm;codecs=opus'
  })

  const chunks: Blob[] = []

  return new Promise((resolve) => {
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data)
    }

    mediaRecorder.onstop = () => {
      resolve(new Blob(chunks, { type: 'audio/webm' }))
    }

    mediaRecorder.start()

    // 模拟停止（实际应该由用户触发）
    setTimeout(() => mediaRecorder.stop(), 5000)
  })
}

// WAV 转换
async function convertToWav(webmBlob: Blob): Promise<Blob> {
  const audioContext = new AudioContext()
  const arrayBuffer = await webmBlob.arrayBuffer()
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
  const wavBuffer = audioBufferToWav(audioBuffer)

  audioContext.close()
  return new Blob([wavBuffer], { type: 'audio/wav' })
}
```

### 3. 思考过程展示

```typescript
// 处理节点事件
case 'node_finished':
  // 只保存特定节点的输出（可根据需要过滤）
  if (isTargetNode(event.node_id)) {
    assistantMessage.nodeOutputs[event.node_id] = {
      title: event.title,
      node_type: event.node_type,
      status: event.status,
      outputs: event.outputs,
      inputs: event.inputs,
      elapsedTime: event.metadata?.elapsed_time
    }
  }
  break

// 在组件中渲染
<template v-if="msg.nodeOutputs">
  <div class="thinking-process">
    <div @click="toggleThinking">
      🤔 思考过程 ({{ Object.keys(msg.nodeOutputs).length }}个节点)
    </div>
    <div v-if="expanded">
      <div v-for="(output, nodeId) in msg.nodeOutputs" :key="nodeId">
        <span>{{ output.status === 'succeeded' ? '✅' : '❌' }}</span>
        <span>{{ output.elapsedTime?.toFixed(2) }}s</span>
        <pre>{{ formatOutput(output.outputs) }}</pre>
      </div>
    </div>
  </div>
</template>
```

### 4. 历史记录加载

```typescript
// 完整流程
async function loadHistory() {
  // 1. 获取最新对话
  const conversations = await getConversations(1)

  if (conversations.data.length === 0) {
    return // 无历史记录
  }

  const latestConv = conversations.data[0]

  // 2. 获取对话消息
  const messages = await getMessages(latestConv.id, 50)

  // 3. 重建消息列表
  this.currentConversationId = latestConv.id
  this.messages = []

  for (const msg of messages.data) {
    // 用户消息
    if (msg.query) {
      this.messages.push({
        id: `user_${msg.id}`,
        role: 'user',
        content: msg.query,
        files: msg.message_files
          ?.filter(f => f.belongs_to === 'user')
          .map(f => ({
            id: f.id,
            type: f.type,
            url: f.url.startsWith('/files/')
              ? `${baseUrl}${f.url}`
              : f.url
          }))
      })
    }

    // 助手消息
    if (msg.answer) {
      this.messages.push({
        id: `assistant_${msg.id}`,
        role: 'assistant',
        content: msg.answer
      })
    }
  }
}
```

---

## 完整调用示例

### 示例 1: 简单对话

```typescript
// 1. 初始化
const difyStore = useDifyStore()
await difyStore.initConfig()

// 2. 发送消息
try {
  await difyStore.sendMessage('你好，介绍一下你自己')
} catch (error) {
  console.error('发送失败:', error)
}
```

### 示例 2: 带文件的对话

```typescript
// 1. 上传文件
const fileInput = document.querySelector('input[type="file"]')
const file = fileInput.files[0]

const uploadResult = await uploadFile(file)

// 2. 发送消息
await difyStore.sendMessage('请分析这个文件', [{
  type: 'image',
  transfer_method: 'local_file',
  upload_file_id: uploadResult.id
}])
```

### 示例 3: 语音输入

```typescript
// 1. 录制音频
const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
const mediaRecorder = new MediaRecorder(stream)
const chunks: Blob[] = []

mediaRecorder.ondataavailable = (e) => chunks.push(e.data)

mediaRecorder.start()
// ... 用户录音 ...
mediaRecorder.stop()

// 2. 等待录音完成
const audioBlob = await new Promise(resolve => {
  mediaRecorder.onstop = () => {
    resolve(new Blob(chunks, { type: 'audio/webm' }))
  }
})

// 3. 转换为 WAV
const wavBlob = await convertToWav(audioBlob)

// 4. 语音转文字
const text = await audioToText(wavBlob, 'wav')

// 5. 发送消息
await difyStore.sendMessage(text)
```

### 示例 4: 获取历史记录

```typescript
// 1. 加载历史
const history = await loadConversationHistory()

if (history) {
  // 2. 设置对话 ID
  difyStore.currentConversationId = history.conversationId

  // 3. 恢复消息
  difyStore.messages = history.messages.map(msg => ({
    id: msg.id,
    role: msg.role,
    content: msg.content,
    createdAt: new Date(msg.created_at * 1000)
  }))
}
```

---

## 错误处理

### 常见错误类型

```typescript
// 1. 配置错误
if (!difyStore.config.token || !difyStore.config.baseUrl) {
  throw new Error('Dify 配置未初始化')
}

// 2. 网络错误
try {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
} catch (error) {
  if (error.name === 'TypeError') {
    throw new Error('网络连接失败，请检查网络设置')
  }
  throw error
}

// 3. API 错误
const data = await response.json()
if (data.code) {
  switch (data.code) {
    case 'invalid_api_token':
      throw new Error('API Token 无效')
    case 'rate_limit_exceeded':
      throw new Error('请求频率过高，请稍后重试')
    default:
      throw new Error(data.message || '未知错误')
  }
}
```

### 错误处理示例

```typescript
async function safeSendMessage(query: string) {
  try {
    // 验证配置
    if (!difyStore.isConfigured) {
      await difyStore.initConfig()
    }

    // 验证输入
    if (!query.trim()) {
      throw new Error('请输入消息内容')
    }

    // 发送消息
    await difyStore.sendMessage(query)

  } catch (error) {
    // 错误分类处理
    if (error.message.includes('network')) {
      ElMessage.error('网络错误，请检查连接')
    } else if (error.message.includes('token')) {
      ElMessage.error('API 配置错误，请联系管理员')
    } else {
      ElMessage.error(`发送失败: ${error.message}`)
    }

    // 记录错误
    console.error('[Dify] Send message failed:', error)
  }
}
```

---

## 最佳实践

### 1. 配置管理

```typescript
// ✅ 推荐：集中管理配置
const config = {
  get token() { return difyStore.config.token },
  get baseUrl() { return difyStore.config.baseUrl.replace(/\/$/, '') }
}

// ❌ 避免：硬编码配置
fetch('https://api.dify.ai/v1/chat-messages', {
  headers: { 'Authorization': 'Bearer app-xxx' }
})
```

### 2. 用户标识

```typescript
// ✅ 推荐：持久化用户 ID
const storageKey = 'dify_user_id'
let userId = sessionStorage.getItem(storageKey)

if (!userId) {
  userId = generateUserId()
  sessionStorage.setItem(storageKey, userId)
}

// ❌ 避免：每次生成新 ID
const userId = 'user_' + Date.now() // 无法维持对话上下文
```

### 3. 流式响应

```typescript
// ✅ 推荐：使用 AsyncGenerator 处理流
for await (const event of parseStream(stream)) {
  handleEvent(event)
}

// ❌ 避免：一次性读取整个流
const text = await stream.text() // 可能导致内存溢出
```

### 4. 错误重试

```typescript
// ✅ 推荐：智能重试
async function sendMessageWithRetry(query: string, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await sendMessage(query)
    } catch (error) {
      if (i === maxRetries - 1) throw error

      // 等待后重试
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
    }
  }
}

// ❌ 避免：无限重试
while (true) {
  try {
    return await sendMessage(query)
  } catch {}
}
```

### 5. 资源清理

```typescript
// ✅ 推荐：及时释放资源
const blobUrl = URL.createObjectURL(blob)
// ... 使用 blobUrl ...
URL.revokeObjectURL(blobUrl) // 释放内存

// ✅ 推荐：清理录音资源
mediaRecorder.stream.getTracks().forEach(track => track.stop())

// ❌ 避免：资源泄漏
const blobUrl = URL.createObjectURL(blob)
// 忘记释放 URL
```

---

## 附录

### A. 完整的配置结构

```typescript
interface DifyConfig {
  // 基础配置
  enabled: boolean              // 是否启用
  token: string                 // API Token
  baseUrl: string               // API 地址

  // UI 配置
  buttonColor: string           // 按钮颜色
  windowWidth: string           // 窗口宽度 (rem)
  windowHeight: string          // 窗口高度 (rem)

  // 可选配置
  welcomeEnabled?: boolean      // 是否显示欢迎语
  welcomeText?: string          // 欢迎语内容
  suggestionsEnabled?: boolean  // 是否显示推荐提问
  suggestions?: string[]        // 推荐提问列表
}
```

### B. 流式事件类型

```typescript
type StreamEventType =
  | 'message'            // 消息片段
  | 'message_end'        // 消息结束
  | 'message_file'       // 文件事件
  | 'message_replace'    // 内容替换
  | 'tts_message'        // TTS 音频
  | 'tts_message_end'    // TTS 结束
  | 'error'              // 错误
  | 'workflow_started'   // 工作流开始
  | 'workflow_finished'  // 工作流结束
  | 'node_started'       // 节点开始
  | 'node_finished'      // 节点结束
  | 'ping'               // 保活
```

### C. 文件类型支持

```typescript
// 图片类型
const imageTypes = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp'
]

// 文档类型
const documentTypes = [
  'application/pdf',
  'text/plain',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]

// 判断文件类型
function getFileType(mimeType: string): 'image' | 'document' {
  return imageTypes.includes(mimeType) ? 'image' : 'document'
}
```

---

## 相关文档

- [Dify 集成功能分析文档](./Dify集成功能分析文档.md)
- [Dify 官方 API 文档](https://docs.dify.ai/guides/application-publishing/publish-app)

---

**文档版本**: v1.0.0
**更新日期**: 2026-04-04
**维护者**: raeazL
