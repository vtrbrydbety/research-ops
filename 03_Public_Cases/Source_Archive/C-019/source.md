# C-019 Source Information

## 来源

- 类型：GitHub Issue
- 仓库：facebookresearch/detectron2
- Issue：#2090
- 标题：Cannot build detectron2
- 链接：https://github.com/facebookresearch/detectron2/issues/2090
- 发布日期：2020-10-02
- 访问日期：2026-08-05

## 关键证据

- Issue 描述：通过 pip 从源码安装 Detectron2 时发生 C++/NVCC 编译错误。
- 关键回复：维护者指出 NVCC 必须匹配 PyTorch CUDA，且 NVCC 与 GCC 组合需兼容；社区还报告升级 Ninja 后成功。
- 最终状态：部分解决；根因范围明确，并有成功版本组合记录。

## 归档文件

- issue.png（已归档：包含仓库、Issue 编号、标题和原始问题可视区域）
