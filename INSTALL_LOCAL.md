# 本地安装 themefinder（修改版）

如果你已经克隆了 themefinder 仓库并修改了代码（如 `sentiment_analysis.txt`），你需要以可编辑模式安装本地版本，而不是从 PyPI 安装。

## 方法 1：使用 pip 可编辑模式安装（推荐）

在 `themefinder` 目录下运行：

```bash
cd "C:\Users\Administrator\Desktop\RMIT Project\Tools\themefinder"
pip install -e .
```

`-e` 表示 "editable"（可编辑）模式，安装后：
- 你的修改会立即生效
- 不需要重新安装
- 可以直接 `import themefinder` 使用

## 方法 2：使用 Poetry（如果已安装）

```bash
cd "C:\Users\Administrator\Desktop\RMIT Project\Tools\themefinder"
poetry install
```

Poetry 默认就是可编辑模式安装。

## 方法 3：直接从本地路径安装（非可编辑）

如果你不需要可编辑模式，也可以：

```bash
pip install "C:\Users\Administrator\Desktop\RMIT Project\Tools\themefinder"
```

但这种方式修改代码后需要重新安装。

## 验证安装

安装后，可以通过以下方式验证：

```python
import themefinder
print(themefinder.__version__)

# 检查文件路径，确认使用的是本地版本
import themefinder.tasks
print(themefinder.tasks.__file__)
# 应该显示本地路径，而不是 site-packages 中的路径
```

## 注意事项

- 确保在虚拟环境中安装，避免影响系统 Python
- 如果有多个 Python 环境，确保在正确的环境中安装
- 如果之前已经用 `pip install themefinder` 安装了 PyPI 版本，建议先卸载：`pip uninstall themefinder`，然后再安装本地版本


