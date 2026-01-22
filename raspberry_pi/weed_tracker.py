"""
Simple SORT Tracker for Weed Detection
Based on Simple Online and Realtime Tracking (SORT)

ติดตาม ID ของหญ้าแต่ละต้นข้ามเฟรม
ป้องกันการพ่นซ้ำต้นเดิม
"""

import numpy as np
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field


@dataclass
class TrackedObject:
    """วัตถุที่ถูก track"""
    id: int
    x: int
    y: int
    width: int
    height: int
    class_name: str
    confidence: float
    is_target: bool
    frames_since_seen: int = 0
    sprayed: bool = False


class SimpleTracker:
    """
    Simple tracker using IoU matching
    ไม่ใช้ Kalman Filter เพื่อความเบา
    """
    
    def __init__(
        self,
        max_frames_missing: int = 10,
        iou_threshold: float = 0.3
    ):
        self.next_id = 1
        self.tracked_objects: Dict[int, TrackedObject] = {}
        self.sprayed_ids: Set[int] = set()  # IDs ที่พ่นไปแล้ว
        
        self.max_frames_missing = max_frames_missing
        self.iou_threshold = iou_threshold
    
    def update(self, detections: list) -> List[TrackedObject]:
        """
        อัพเดท tracker ด้วย detections ใหม่
        Returns: list ของ TrackedObject ที่มี ID
        """
        if not detections:
            # ไม่มี detection → เพิ่ม frames_since_seen
            self._age_tracks()
            return list(self.tracked_objects.values())
        
        # แปลง detections เป็น boxes
        det_boxes = []
        for det in detections:
            x1 = det.x - det.width // 2
            y1 = det.y - det.height // 2
            x2 = det.x + det.width // 2
            y2 = det.y + det.height // 2
            det_boxes.append({
                'box': (x1, y1, x2, y2),
                'det': det
            })
        
        # จับคู่ detections กับ tracked objects
        matched, unmatched_dets = self._match_detections(det_boxes)
        
        # อัพเดท matched objects
        for track_id, det_info in matched.items():
            self.tracked_objects[track_id].x = det_info['det'].x
            self.tracked_objects[track_id].y = det_info['det'].y
            self.tracked_objects[track_id].width = det_info['det'].width
            self.tracked_objects[track_id].height = det_info['det'].height
            self.tracked_objects[track_id].confidence = det_info['det'].confidence
            self.tracked_objects[track_id].frames_since_seen = 0
        
        # สร้าง tracks ใหม่สำหรับ unmatched detections
        for det_info in unmatched_dets:
            det = det_info['det']
            new_obj = TrackedObject(
                id=self.next_id,
                x=det.x,
                y=det.y,
                width=det.width,
                height=det.height,
                class_name=det.class_name,
                confidence=det.confidence,
                is_target=det.is_target,
                sprayed=False
            )
            self.tracked_objects[self.next_id] = new_obj
            self.next_id += 1
        
        # ลบ tracks เก่าที่หายไปนาน
        self._age_tracks()
        
        return list(self.tracked_objects.values())
    
    def _match_detections(self, det_boxes: List[dict]):
        """จับคู่ detections กับ tracked objects ด้วย IoU"""
        matched = {}
        unmatched_dets = det_boxes.copy()
        
        if not self.tracked_objects:
            return matched, unmatched_dets
        
        # สร้าง IoU matrix
        track_ids = list(self.tracked_objects.keys())
        
        for track_id in track_ids:
            track = self.tracked_objects[track_id]
            track_box = (
                track.x - track.width // 2,
                track.y - track.height // 2,
                track.x + track.width // 2,
                track.y + track.height // 2
            )
            
            best_iou = 0
            best_det_idx = -1
            
            for i, det_info in enumerate(unmatched_dets):
                iou = self._calculate_iou(track_box, det_info['box'])
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_det_idx = i
            
            if best_det_idx >= 0:
                matched[track_id] = unmatched_dets.pop(best_det_idx)
        
        return matched, unmatched_dets
    
    def _calculate_iou(self, box1, box2) -> float:
        """คำนวณ Intersection over Union"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union_area = box1_area + box2_area - inter_area
        
        if union_area == 0:
            return 0
        
        return inter_area / union_area
    
    def _age_tracks(self):
        """เพิ่ม age และลบ tracks เก่า"""
        to_delete = []
        for track_id, track in self.tracked_objects.items():
            track.frames_since_seen += 1
            if track.frames_since_seen > self.max_frames_missing:
                to_delete.append(track_id)
        
        for track_id in to_delete:
            del self.tracked_objects[track_id]
    
    def mark_sprayed(self, track_id: int):
        """ทำเครื่องหมายว่าพ่นแล้ว"""
        if track_id in self.tracked_objects:
            self.tracked_objects[track_id].sprayed = True
        self.sprayed_ids.add(track_id)
    
    def is_sprayed(self, track_id: int) -> bool:
        """ตรวจสอบว่าพ่นไปแล้วหรือยัง"""
        return track_id in self.sprayed_ids
    
    def get_unsprayed_targets(self, min_x: int = 0) -> List[TrackedObject]:
        """
        หา targets ที่ยังไม่ได้พ่น และอยู่ด้านหน้า (X >= min_x)
        
        min_x: ตำแหน่งขั้นต่ำ (0 = center, บวก = ข้างหน้า)
        """
        result = []
        for track in self.tracked_objects.values():
            if track.is_target and not track.sprayed:
                # คำนวณ distance from center
                distance_x = track.x - 320  # assuming 640 width
                if distance_x >= min_x:
                    result.append(track)
        
        # เรียงตาม X (ใกล้ center ที่สุดก่อน)
        result.sort(key=lambda t: abs(t.x - 320))
        return result
    
    def reset(self):
        """Reset tracker"""
        self.tracked_objects.clear()
        self.sprayed_ids.clear()
        self.next_id = 1
