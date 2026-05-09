# 片段匹配功能 - 实现文档

## 功能概述

实现了一个基于关键词的本地匹配系统，用于快速定位用户截图对应的表单填写步骤。

## 架构流程

```
用户截图
  ↓
Python上传到Dify
  ↓
调用本地OCR提取关键词
  ↓
本地匹配fragments_structured.json
  ↓
构建上下文（片段信息+操作说明+注意事项）
  ↓
调用Dify Chat API（带上上下文）
  ↓
AI基于匹配片段给出精确回答
```

## 核心模块

### 1. fragment_matcher.py - 片段匹配器

**匹配策略（三层混合匹配）：**

1. **第一层：完全匹配**（≥2个关键词）
   - 计算OCR关键词与片段keywords的交集
   - 交集大小≥2即匹配成功
   - 加上稀有关键词加权

2. **第二层：稀有关键词匹配**（1个）
   - 匹配出现频率≤2的关键词
   - 避免高频词（如"人脸识别"）误匹配

3. **第三层：部分匹配**（≥2个）
   - 支持包含关系（OCR识别错误时）
   - 例如："社保" 匹配 "社保信息"

**API：**
```python
matcher = get_matcher()
fragment, method, score = matcher.match_hybrid(ocr_keywords)
```

### 2. ocr_extractor.py - OCR提取器

使用Dify Chat API从截图提取关键词：

```python
extractor = OCRExtractor(dify_base_url, dify_token)
keywords = extractor.extract_keywords_from_image(file_id, user_id)
```

**提取策略：**
- 专用prompt提取标题、按钮、标签文字
- 返回JSON格式的关键词列表
- 降级方案：正则提取中文短语

### 3. form_helper.py - HTTP代理增强

新增API端点：`POST /api/match-fragment`

**请求：**
```json
{
  "image_file_id": "dify-upload-file-id"
}
```

**响应：**
```json
{
  "success": true,
  "fragment": {
    "id": 35,
    "title": "社保信息填写",
    "step_label": "第11步 · 填写申请信息",
    "keywords": ["社保信息", "咨询电话12333", "是否申请社保"],
    "tips": "社保可先不申请...",
    "context_text": "原始操作说明...",
    "image_file": "page18/img_4.jpeg"
  },
  "match_method": "完全匹配3个关键词",
  "match_score": 45.0,
  "extracted_keywords": ["社保信息", "是否申请社保", "咨询电话12333"]
}
```

### 4. chat.html - 前端集成

修改 `sendScreenshotHelp()` 函数：

1. 先调用 `/api/match-fragment` 获取匹配片段
2. 构建上下文信息（步骤+标题+关键词+注意事项+操作说明）
3. 将上下文拼接到query中
4. 调用Dify API获取AI回答

## 测试结果

```
============================================================
测试片段匹配功能
============================================================

测试: 社保信息页面
✅ 通过 - 匹配到: 社保信息填写 (ID: 35)
   方法: 完全匹配3个关键词, 分数: 45.0

测试: 税务信息页面
✅ 通过 - 匹配到: 多证合一-税务信息填写 (ID: 32)
   方法: 完全匹配4个关键词, 分数: 58.0

测试: 公安信息页面
✅ 通过 - 匹配到: 公安信息-免费刻章选择 (ID: 34)
   方法: 完全匹配3个关键词, 分数: 45.0

测试: 人脸识别验证
✅ 通过 - 匹配到: 人脸识别验证页面1 (ID: 45)
   方法: 完全匹配2个关键词, 分数: 26.0

测试: 预约银行开户
✅ 通过 - 匹配到: 预约银行开户及代扣选择 (ID: 40)
   方法: 完全匹配3个关键词, 分数: 45.0

============================================================
测试结果: 5 通过, 0 失败
============================================================
```

## 关键设计点

### 1. 关键词人工整理
**原因：** 截图文字多，只有特定标题/按钮是可靠标识
**策略：** 每个片段3-8个人工整理的keywords

### 2. 注意事项挂载到片段
**优势：** 匹配到片段自动带出踩坑经验，无需单独文档
**实现：** `fragment.tips` 字段

### 3. 本地匹配而非RAG
**原因：** 精确可控，性能好
**实现：** 纯代码逻辑，不走向量数据库

### 4. 匹配分数设计
```python
# 完全匹配: 10分/关键词
# 部分匹配: 5分/关键词
# 稀有加权: 频率1次+5分, 2次+3分, 3次+1分
```

## 使用方法

### 启动应用
```bash
./start.sh  # macOS
start.bat   # Windows
```

### 测试匹配功能
```bash
python3 test_matcher.py
```

### 调试日志
应用运行时会在终端显示匹配日志：
```
[match] 收到匹配请求, image_file_id=xxx
[match] OCR提取关键词: ['社保信息', '是否申请社保']
[match] 匹配成功: 社保信息填写 (完全匹配2个关键词, 分数=45.0)
```

## 优化方向

### 1. 增加keywords数量
当前平均3.3个/片段，建议增加到5-7个以提高匹配准确率

### 2. 分层关键词
```json
{
  "primary_keywords": ["社保信息"],      // 主标识
  "secondary_keywords": ["是否申请社保"], // 次标识
  "context_keywords": ["咨询电话12333"]   // 上下文
}
```

### 3. OCR容错优化
- 同义词映射：{"免费刻章": "是否免费刻章"}
- 错字纠正：{"刻章": "剢章"}

### 4. 匹配缓存
缓存最近N次匹配结果，避免重复OCR

## 文件清单

```
form_helper.py              # 主程序（增强）
chat.html                   # 前端（增强）
fragment_matcher.py         # 匹配器（新增）
ocr_extractor.py            # OCR提取器（新增）
fragments_structured.json   # 片段数据（已存在）
test_matcher.py             # 测试脚本（新增）
```

## 性能指标

- 匹配速度：本地计算 < 10ms
- OCR提取：Dify API ≈ 2-5秒
- 总响应时间：≈ 3-8秒（含网络）
- 匹配准确率：测试用例 100% (5/5)

## 故障排查

### OCR提取失败
检查Dify API配置：
```bash
# 查看config.json
cat config.json
```

### 匹配失败
检查keywords完整性：
```bash
python3 -c "import json; f=open('fragments_structured.json'); data=json.load(f); print(f'Total: {len(data)}'); print(f'Empty keywords: {sum(1 for x in data if not x.get(\"keywords\"))}')"
```

### API调用失败
查看代理日志：
```
[proxy] POST /api/match-fragment
[match] 收到匹配请求
[match] ERROR: ...
```
