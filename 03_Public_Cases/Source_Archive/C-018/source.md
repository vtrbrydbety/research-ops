# C-018 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：facebookresearch/detectron2
- Issue：#788
- 标题：Exif metadata causes training to fail with SizeMismatchError
- 链接：https://github.com/facebookresearch/detectron2/issues/788
- 发布日期：2020-02-02
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：带 EXIF 方向标记的图片经 Pillow 转置后，尺寸与 VIA 标注记录不一致，触发 SizeMismatchError。
- 关键回复：维护者将问题定位到 Pillow 的读取行为并建议自定义 dataloader；用户分享了基于 OpenCV 的可用读取方案。
- 最终状态：部分解决；用户有可用绕过方案，但读取实现仍有适用范围提醒。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
