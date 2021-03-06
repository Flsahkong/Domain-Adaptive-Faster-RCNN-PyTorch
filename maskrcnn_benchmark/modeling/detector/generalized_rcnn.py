# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
"""
Implements the Generalized R-CNN framework
"""

import torch
from torch import nn

from maskrcnn_benchmark.structures.image_list import to_image_list

from ..backbone import build_backbone
from ..rpn.rpn import build_rpn
from ..roi_heads.roi_heads import build_roi_heads
from ..da_heads.da_heads import build_da_heads


class GeneralizedRCNN(nn.Module):
    """
    Main class for Generalized R-CNN. Currently supports boxes and masks.
    It consists of three main parts:
    - backbone
    - rpn
    - heads: takes the features + the proposals from the RPN and computes
        detections / masks from it.
    """
    # 这里的文件,大部分内容都是原本的maskrcnn-benchmark中有的,只有我标注的地方是DA新加的
    def __init__(self, cfg):
        super(GeneralizedRCNN, self).__init__()

        self.backbone = build_backbone(cfg)
        self.rpn = build_rpn(cfg)
        self.roi_heads = build_roi_heads(cfg)
        # DA start
        self.da_heads = build_da_heads(cfg)
        # DA end

    def forward(self, images, targets=None):
        """
        Arguments:
            images (list[Tensor] or ImageList): images to be processed
            targets (list[BoxList]): ground-truth boxes present in the image (optional)

        Returns:
            result (list[BoxList] or dict[Tensor]): the output from the model.
                During training, it returns a dict[Tensor] which contains the losses.
                During testing, it returns list[BoxList] contains additional fields
                like `scores`, `labels` and `mask` (for Mask R-CNN models).

        """
        if self.training and targets is None:
            raise ValueError("In training mode, targets should be passed")
        images = to_image_list(images)
        features = self.backbone(images.tensors)
        proposals, proposal_losses = self.rpn(images, features, targets)
        # DA start
        da_losses = {}
        # DA end
        if self.roi_heads:
            # DA start
            # 这里的x是proposal对应的feature经过特征提取后的feature
            # 如果是训练阶段，result是修改后的proposal，而非预测的结果（proposal+bbox）
            # 如果是测试阶段，则result是最终的结果（proposal+bbox）
            x, result, detector_losses, da_ins_feas, da_ins_labels = self.roi_heads(features, proposals, targets)

            if self.da_heads:
                da_losses = self.da_heads(features, da_ins_feas, da_ins_labels, targets)
            # DA end

        else:
            # RPN-only models don't have roi_heads
            x = features
            result = proposals
            detector_losses = {}

        if self.training:
            losses = {}
            losses.update(detector_losses)
            losses.update(proposal_losses)
            # DA start
            losses.update(da_losses)
            # DA end
            return losses

        return result
