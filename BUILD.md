# 打包分发手册

## 环境准备

```bash
pip3 install pyinstaller wxPython
```

## macOS 打包

```bash
cd /Users/vinson/Documents/www/gw

python3 -m PyInstaller \
  --name "表单填写助手" \
  --windowed \
  --noconfirm \
  --add-data "chat.html:." \
  --add-data "fragments_structured.json:." \
  --hidden-import fragment_matcher \
  --add-data "page01:page01" \
  --add-data "page02:page02" \
  --add-data "page03:page03" \
  --add-data "page04:page04" \
  --add-data "page05:page05" \
  --add-data "page06:page06" \
  --add-data "page07:page07" \
  --add-data "page08:page08" \
  --add-data "page09:page09" \
  --add-data "page10:page10" \
  --add-data "page11:page11" \
  --add-data "page12:page12" \
  --add-data "page13:page13" \
  --add-data "page14:page14" \
  --add-data "page15:page15" \
  --add-data "page16:page16" \
  --add-data "page17:page17" \
  --add-data "page18:page18" \
  --add-data "page19:page19" \
  --add-data "page20:page20" \
  --add-data "page21:page21" \
  --add-data "page22:page22" \
  --add-data "page23:page23" \
  --add-data "page24:page24" \
  --add-data "page25:page25" \
  --add-data "page26:page26" \
  --add-data "page27:page27" \
  --add-data "page28:page28" \
  --add-data "page29:page29" \
  --add-data "page30:page30" \
  --add-data "page31:page31" \
  --add-data "page32:page32" \
  --add-data "page33:page33" \
  --add-data "page34:page34" \
  --add-data "page35:page35" \
  --add-data "page36:page36" \
  --add-data "page37:page37" \
  --add-data "page38:page38" \
  --add-data "page39:page39" \
  form_helper.py
```

产出：
- `dist/表单填写助手.app` — macOS 应用，双击运行

## Windows 打包

在 Windows 机器上执行相同命令，去掉 `--windowed` 改用 `--noconsole`：

```cmd
pip install pyinstaller wxPython

python -m PyInstaller ^
  --name "表单填写助手" ^
  --noconsole ^
  --noconfirm ^
  --add-data "chat.html;." ^
  --add-data "fragments_structured.json;." ^
  --hidden-import fragment_matcher ^
  --add-data "page01;page01" ^
  ...（同上，分号分隔）...
  form_helper.py
```

产出：`dist/表单填写助手.exe`

## 分发

```bash
# macOS: 压缩成 zip
cd dist
zip -r 表单填写助手-macOS.zip 表单填写助手.app

# Windows: 直接分发 dist/表单填写助手/ 目录
```

## 自定义配置

在应用同级目录创建 `config.json` 可覆盖默认配置：

```json
{
  "difyApi": "http://your-dify-server:8889",
  "difyToken": "app-xxxxxxxx",
  "formUrl": "https://your-form-url"
}
```

## 注意事项

- macOS 打包产物只能在 macOS 上运行，Windows 同理
- `--windowed` 模式不显示终端窗口，调试时去掉此参数可看日志
- 首次打开 macOS 应用可能提示"无法验证开发者"，右键 → 打开即可
- 打包前确保 `form_helper.py` 的 `SCRIPT_DIR` 使用了 `sys._MEIPASS` 兼容路径
