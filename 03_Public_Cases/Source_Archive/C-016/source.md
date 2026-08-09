# C-016 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：facebookresearch/detectron2
- Issue：#863
- 标题：SizeMismatch with custom annotations
- 链接：https://github.com/facebookresearch/detectron2/issues/863
- 发布日期：2020-02-13
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：自定义 COCO 数据触发图像尺寸不匹配；手机图片的 EXIF 方向导致读取后的宽高与标注坐标系不一致。
- 关键回复：维护者解释 Pillow 会依据 EXIF 转置图像；用户避开含 EXIF 的手机图片后错误消失。
- 最终状态：已解决。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
