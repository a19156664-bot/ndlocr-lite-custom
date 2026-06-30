from __future__ import annotations

from typing import Any

import numpy as np
from sahi.predict import get_sliced_prediction
from sahi.prediction import ObjectPrediction


class DeimObjectPrediction(ObjectPrediction):
    """
    NDLOCR-Lite の DEIM が返す pred_char_count をSAHI推論後も保持するための拡張。
    NMSならこの属性は維持される。
    GREEDYNMM/NMMはSAHI側で新しい ObjectPrediction を作るため、保持できない場合がある。
    """

    def __init__(self, *args: Any, pred_char_count: float = 100.0, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pred_char_count = float(pred_char_count)

    def get_shifted_object_prediction(self):
        shifted = super().get_shifted_object_prediction()
        segmentation = shifted.mask.segmentation if shifted.mask else None
        full_shape = shifted.mask.full_shape if shifted.mask else None

        return DeimObjectPrediction(
            bbox=shifted.bbox.to_xyxy(),
            category_id=shifted.category.id,
            category_name=shifted.category.name,
            score=shifted.score.value,
            segmentation=segmentation,
            shift_amount=[0, 0],
            full_shape=full_shape,
            pred_char_count=self.pred_char_count,
        )


class DEIMSahiDetectionModel:
    """
    SAHI の DetectionModel 相当のduck-typingラッパー。
    torch依存を避けるため、sahi.models.base.DetectionModel は継承しない。
    """

    def __init__(self, detector) -> None:
        self.model = detector
        self.confidence_threshold = float(detector.conf_threshold)
        self._original_predictions = None
        self._object_prediction_list_per_image = []
        self._batch_images = None

    def perform_inference(self, image: np.ndarray) -> None:
        # SAHI側の confidence_threshold を DEIM の conf_threshold に同期
        self.model.conf_threshold = float(self.confidence_threshold)
        self._original_predictions = self.model.detect(image)

    def perform_batch_inference(self, images: list[np.ndarray]) -> None:
        # DEIM はネイティブbatch推論を持たないので、convert時に順次実行する
        self._batch_images = images

    def convert_original_predictions(self, shift_amount=None, full_shape=None) -> None:
        if self._batch_images is not None:
            shifts = _normalize_list_arg(shift_amount, len(self._batch_images), default=[0, 0])
            shapes = _normalize_list_arg(full_shape, len(self._batch_images), default=None)

            grouped_predictions = []
            for image, shift, shape in zip(self._batch_images, shifts, shapes):
                self.perform_inference(np.ascontiguousarray(image))
                grouped_predictions.append(
                    self._convert_one_image_predictions(
                        shift_amount=shift,
                        full_shape=shape,
                    )
                )

            self._object_prediction_list_per_image = grouped_predictions
            self._batch_images = None
            return

        shift = _normalize_single_arg(shift_amount, default=[0, 0])
        shape = _normalize_single_arg(full_shape, default=None)
        self._object_prediction_list_per_image = [
            self._convert_one_image_predictions(
                shift_amount=shift,
                full_shape=shape,
            )
        ]

    def _convert_one_image_predictions(self, shift_amount, full_shape):
        object_predictions = []

        if self._original_predictions is None:
            return object_predictions

        for det in self._original_predictions:
            score = float(det["confidence"])
            if score < float(self.confidence_threshold):
                continue

            x1, y1, x2, y2 = [float(v) for v in det["box"]]
            if x2 <= x1 or y2 <= y1:
                continue

            class_index = int(det["class_index"])
            category_name = det.get("class_name") or self._class_name(class_index)

            object_predictions.append(
                DeimObjectPrediction(
                    bbox=[x1, y1, x2, y2],
                    category_id=class_index,
                    category_name=category_name,
                    score=score,
                    shift_amount=shift_amount,
                    full_shape=full_shape,
                    pred_char_count=float(det.get("pred_char_count", 100.0)),
                )
            )

        return object_predictions

    @property
    def object_prediction_list(self):
        if not self._object_prediction_list_per_image:
            return []
        return self._object_prediction_list_per_image[0]

    @property
    def object_prediction_list_per_image(self):
        return self._object_prediction_list_per_image or []

    def _class_name(self, class_index: int) -> str:
        classes = self.model.classes
        if isinstance(classes, dict):
            return classes.get(class_index) or classes.get(str(class_index)) or str(class_index)
        if isinstance(classes, (list, tuple)) and 0 <= class_index < len(classes):
            return classes[class_index]
        return str(class_index)


class SlicedDEIM:
    """
    既存の detector と同じように .detect(), .classes, .draw_detections() を持つラッパー。
    ocr.py 側は detector.detect(img) のまま使える。
    """

    def __init__(
        self,
        detector,
        slice_height: int = 1024,
        slice_width: int = 1024,
        overlap_height_ratio: float = 0.2,
        overlap_width_ratio: float = 0.2,
        postprocess_type: str = "NMS",
        postprocess_match_metric: str = "IOU",
        postprocess_match_threshold: float = 0.5,
        perform_standard_pred: bool = False,
        progress_bar: bool = False,
    ) -> None:
        self.detector = detector
        self.classes = detector.classes
        self.slice_height = slice_height
        self.slice_width = slice_width
        self.overlap_height_ratio = overlap_height_ratio
        self.overlap_width_ratio = overlap_width_ratio
        self.postprocess_type = postprocess_type
        self.postprocess_match_metric = postprocess_match_metric
        self.postprocess_match_threshold = postprocess_match_threshold
        self.perform_standard_pred = perform_standard_pred
        self.progress_bar = progress_bar
        self.sahi_model = DEIMSahiDetectionModel(detector)

    def detect(self, img: np.ndarray):
        result = get_sliced_prediction(
            image=img,
            detection_model=self.sahi_model,
            slice_height=self.slice_height,
            slice_width=self.slice_width,
            overlap_height_ratio=self.overlap_height_ratio,
            overlap_width_ratio=self.overlap_width_ratio,
            perform_standard_pred=self.perform_standard_pred,
            postprocess_type=self.postprocess_type,
            postprocess_match_metric=self.postprocess_match_metric,
            postprocess_match_threshold=self.postprocess_match_threshold,
            postprocess_class_agnostic=False,
            auto_slice_resolution=False,
            verbose=1,
            progress_bar=self.progress_bar,
            confidence_threshold=self.detector.conf_threshold,
            force_postprocess_type=True,
        )

        detections = []
        h, w = img.shape[:2]

        for obj in result.object_prediction_list:
            x1, y1, x2, y2 = obj.bbox.to_xyxy()
            x1 = int(max(0, min(round(x1), w)))
            x2 = int(max(0, min(round(x2), w)))
            y1 = int(max(0, min(round(y1), h)))
            y2 = int(max(0, min(round(y2), h)))

            if x2 <= x1 or y2 <= y1:
                continue

            class_index = int(obj.category.id)

            detections.append(
                {
                    "class_index": class_index,
                    "confidence": float(obj.score.value),
                    "box": np.array([x1, y1, x2, y2], dtype=np.int32),
                    "pred_char_count": float(getattr(obj, "pred_char_count", 100.0)),
                    "class_name": obj.category.name,
                }
            )

        return detections

    def draw_detections(self, npimg: np.ndarray, detections: list):
        return self.detector.draw_detections(npimg, detections)


def _normalize_single_arg(value, default):
    if value is None:
        return default
    if isinstance(value, (list, tuple)) and len(value) > 0:
        first = value[0]
        if isinstance(first, (list, tuple)):
            return list(first)
        return list(value)
    return default


def _normalize_list_arg(value, n: int, default):
    if value is None:
        return [default for _ in range(n)]

    if not isinstance(value, (list, tuple)) or len(value) == 0:
        return [default for _ in range(n)]

    first = value[0]

    # [x, y] のような単一値
    if not isinstance(first, (list, tuple)):
        return [list(value) for _ in range(n)]

    # [[x, y], [x, y], ...]
    normalized = [list(v) if v is not None else default for v in value]

    if len(normalized) < n:
        normalized.extend([default for _ in range(n - len(normalized))])

    return normalized[:n]