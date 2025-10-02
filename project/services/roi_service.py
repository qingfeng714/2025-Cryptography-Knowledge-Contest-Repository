import numpy as np

def segmentROI(image):
    """
    ROI segmentation placeholder.
    输入: image (numpy array)
    输出: mask (numpy array, bool), 标记需要加密/保护的区域
    """
    # TODO: 使用 nnUNet 或 UNet 预测 mask
    if image is None:
        # 示例：返回全 False mask
        mask = np.zeros((256, 256), dtype=bool)
    else:
        # 简单示例：中心区域为 ROI
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=bool)
        mask[h//4:3*h//4, w//4:3*w//4] = True
    return mask
