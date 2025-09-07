#!/usr/bin/env python3
"""
名片智能裁切與增強服務
整合 CardProcessor 核心功能到名片管理系統
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance
import os
import logging
from typing import Optional, Tuple, List
import tempfile
import gc
import psutil
from datetime import datetime

# 設置日誌
logger = logging.getLogger(__name__)

class CardEnhancementService:
    """
    名片智能增強服務
    提供智能裁切、透視校正和品質增強功能
    """
    
    def __init__(self, manual_coords: Optional[List[int]] = None):
        """
        初始化增強服務
        
        Args:
            manual_coords: 手動指定的座標 [x1, y1, x2, y2]
        """
        self.manual_coords = manual_coords or [150, 440, 1130, 840]  # 預設座標
        self.enabled = os.getenv("USE_CARD_ENHANCEMENT", "true").lower() == "true"
        logger.info(f"卡片增強服務初始化，啟用狀態: {self.enabled}")
    
    def detect_card_edges(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        自動檢測名片邊緣
        
        Args:
            image: OpenCV 圖片數組
            
        Returns:
            名片四個角點座標，失敗時返回 None
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 增強對比度
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Canny邊緣檢測
            edges = cv2.Canny(enhanced, 50, 150)
            
            # 形態學閉運算
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            # 找輪廓
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
                
            # 找最大輪廓
            largest = max(contours, key=cv2.contourArea)
            
            # 檢查面積是否合理
            image_area = gray.shape[0] * gray.shape[1]
            if cv2.contourArea(largest) < image_area * 0.1:
                return None
                
            # 獲取邊界框
            x, y, w, h = cv2.boundingRect(largest)
            
            # 檢查寬高比是否合理（名片通常是 1.5-1.8）
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 1.3 or aspect_ratio > 2.0:
                return None
                
            return np.array([
                [x, y],
                [x + w, y],
                [x + w, y + h],
                [x, y + h]
            ], dtype=np.float32)
            
        except Exception as e:
            logger.error(f"邊緣檢測失敗: {e}")
            return None
    
    def auto_detect_coordinates(self, image: np.ndarray) -> List[int]:
        """
        智能檢測名片座標，結合內容分析
        
        Args:
            image: OpenCV 圖片數組
            
        Returns:
            檢測到的座標 [x1, y1, x2, y2]
        """
        try:
            h, w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 方法1: 嘗試邊緣檢測
            corners = self.detect_card_edges(image)
            if corners is not None:
                x1, y1 = int(corners[0][0]), int(corners[0][1])
                x2, y2 = int(corners[2][0]), int(corners[2][1])
                return [x1, y1, x2, y2]
            
            # 方法2: 基於亮度變化檢測內容區域
            row_means = np.mean(gray, axis=1)
            col_means = np.mean(gray, axis=0)
            
            # 找到亮度變化最大的區域
            row_diff = np.abs(np.diff(row_means))
            col_diff = np.abs(np.diff(col_means))
            
            # 找到上下邊界
            center_y = h // 2
            top_boundary = center_y
            bottom_boundary = center_y
            
            threshold_row = np.percentile(row_diff, 70)
            for i in range(center_y, 0, -1):
                if i-1 < len(row_diff) and row_diff[i-1] > threshold_row:
                    top_boundary = max(0, i - 20)
                    break
            
            for i in range(center_y, h-1):
                if i < len(row_diff) and row_diff[i] > threshold_row:
                    bottom_boundary = min(h-1, i + 20)
                    break
            
            # 找到左右邊界
            center_x = w // 2
            left_boundary = center_x
            right_boundary = center_x
            
            threshold_col = np.percentile(col_diff, 70)
            for i in range(center_x, 0, -1):
                if i-1 < len(col_diff) and col_diff[i-1] > threshold_col:
                    left_boundary = max(0, i - 20)
                    break
            
            for i in range(center_x, w-1):
                if i < len(col_diff) and col_diff[i] > threshold_col:
                    right_boundary = min(w-1, i + 20)
                    break
            
            # 方法3: 如果檢測範圍太小，使用保守策略
            detected_width = right_boundary - left_boundary
            detected_height = bottom_boundary - top_boundary
            
            if detected_width < w * 0.3 or detected_height < h * 0.3:
                margin_x = int(w * 0.1)
                margin_y = int(h * 0.15)
                left_boundary = margin_x
                right_boundary = w - margin_x
                top_boundary = margin_y
                bottom_boundary = h - margin_y
            
            return [left_boundary, top_boundary, right_boundary, bottom_boundary]
            
        except Exception as e:
            logger.error(f"自動檢測座標失敗: {e}")
            # 返回基於圖片比例的保守座標
            margin_x = int(w * 0.1)
            margin_y = int(h * 0.15)
            return [margin_x, margin_y, w - margin_x, h - margin_y]
    
    def perspective_transform(self, image: np.ndarray, corners: np.ndarray) -> np.ndarray:
        """
        透視變換矯正名片
        
        Args:
            image: 原始圖片
            corners: 四個角點座標
            
        Returns:
            矯正後的圖片
        """
        try:
            # 排序頂點
            rect = np.zeros((4, 2), dtype="float32")
            s = corners.sum(axis=1)
            rect[0] = corners[np.argmin(s)]  # 左上
            rect[2] = corners[np.argmax(s)]  # 右下
            diff = np.diff(corners, axis=1)
            rect[1] = corners[np.argmin(diff)]  # 右上
            rect[3] = corners[np.argmax(diff)]  # 左下
            
            (tl, tr, br, bl) = rect
            
            # 計算新圖片尺寸
            width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            max_width = max(int(width_a), int(width_b))
            
            height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            max_height = max(int(height_a), int(height_b))
            
            if max_width <= 0 or max_height <= 0:
                return image
            
            # 透視變換
            dst = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype="float32")
            
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(image, M, (max_width, max_height))
            
            return warped
            
        except Exception as e:
            logger.error(f"透視變換失敗: {e}")
            return image
    
    def enhance_image(self, image: np.ndarray, scale_factor: int = 3) -> np.ndarray:
        """
        增強圖片品質
        
        Args:
            image: 輸入圖片
            scale_factor: 放大倍數
            
        Returns:
            增強後的圖片
        """
        try:
            # 降噪
            denoised = cv2.fastNlMeansDenoisingColored(image, None, 5, 5, 7, 21)
            
            # 放大
            height, width = denoised.shape[:2]
            new_size = (int(width * scale_factor), int(height * scale_factor))
            enlarged = cv2.resize(denoised, new_size, interpolation=cv2.INTER_LANCZOS4)
            
            # PIL 增強
            pil_image = Image.fromarray(cv2.cvtColor(enlarged, cv2.COLOR_BGR2RGB))
            
            # 銳化
            sharpness = ImageEnhance.Sharpness(pil_image)
            sharpened = sharpness.enhance(2.0)
            
            # 對比度
            contrast = ImageEnhance.Contrast(sharpened)
            enhanced = contrast.enhance(1.3)
            
            # 亮度
            brightness = ImageEnhance.Brightness(enhanced)
            enhanced = brightness.enhance(1.05)
            
            # 轉回 OpenCV 格式
            result = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
            
            # CLAHE 增強
            lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l_channel = clahe.apply(l_channel)
            result = cv2.merge([l_channel, a, b])
            result = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
            
            return result
            
        except Exception as e:
            logger.error(f"圖片增強失敗: {e}")
            return image
    
    def process_image(self, input_path: str, output_path: Optional[str] = None, 
                     scale_factor: int = 3, auto_detect: bool = True) -> Tuple[bool, Optional[str]]:
        """
        處理名片圖片
        
        Args:
            input_path: 輸入圖片路徑
            output_path: 輸出圖片路徑，None 則創建臨時文件
            scale_factor: 放大倍數
            auto_detect: 是否自動檢測
            
        Returns:
            (成功標誌, 輸出路徑)
        """
        if not self.enabled:
            logger.info("名片增強功能已禁用")
            return False, input_path
        
        try:
            # 讀取圖片
            image = cv2.imread(input_path)
            if image is None:
                logger.error(f"無法讀取圖片: {input_path}")
                return False, input_path
            
            # 檢測或使用手動座標
            if auto_detect:
                logger.debug("使用自動檢測模式")
                coords = self.auto_detect_coordinates(image)
                x1, y1, x2, y2 = coords
                corners = np.array([
                    [x1, y1], [x2, y1],
                    [x2, y2], [x1, y2]
                ], dtype=np.float32)
            else:
                logger.debug("使用手動座標模式")
                x1, y1, x2, y2 = self.manual_coords
                corners = np.array([
                    [x1, y1], [x2, y1],
                    [x2, y2], [x1, y2]
                ], dtype=np.float32)
            
            # 透視變換裁切
            logger.debug("執行透視變換")
            cropped = self.perspective_transform(image, corners)
            
            # 品質增強
            logger.debug(f"執行圖片增強，放大倍數: {scale_factor}")
            enhanced = self.enhance_image(cropped, scale_factor)
            
            # 保存結果
            if output_path is None:
                # 創建臨時文件
                temp_fd, output_path = tempfile.mkstemp(suffix='.jpg', prefix='enhanced_card_')
                os.close(temp_fd)  # 關閉文件描述符，但保留文件
            
            success = cv2.imwrite(output_path, enhanced)
            if success:
                logger.info(f"圖片增強完成: {output_path}")
                logger.debug(f"輸出尺寸: {enhanced.shape[1]}x{enhanced.shape[0]}")
                return True, output_path
            else:
                logger.error(f"保存增強圖片失敗: {output_path}")
                return False, input_path
                
        except Exception as e:
            logger.error(f"圖片處理失敗: {e}")
            return False, input_path


class BatchProcessingService:
    """
    批量處理服務
    提供記憶體優化的大批量圖片處理功能
    """
    
    def __init__(self, card_enhancer: Optional[CardEnhancementService] = None):
        """
        初始化批量處理服務
        
        Args:
            card_enhancer: 名片增強服務實例
        """
        self.card_enhancer = card_enhancer or CardEnhancementService()
        self.batch_size = int(os.getenv("BATCH_PROCESSING_SIZE", "5"))
        self.memory_threshold = float(os.getenv("MEMORY_THRESHOLD", "85.0"))  # 85%
        logger.info(f"批量處理服務初始化，批次大小: {self.batch_size}, 記憶體閾值: {self.memory_threshold}%")
    
    def get_memory_usage(self) -> Tuple[float, float, float]:
        """
        獲取當前記憶體使用狀況
        
        Returns:
            (當前使用MB, 總記憶體MB, 使用百分比)
        """
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            total_memory = psutil.virtual_memory().total / 1024 / 1024
            percent = psutil.virtual_memory().percent
            return memory_mb, total_memory, percent
        except Exception as e:
            logger.error(f"獲取記憶體使用狀況失敗: {e}")
            return 0.0, 0.0, 0.0
    
    def cleanup_memory(self) -> None:
        """強制垃圾回收以清理記憶體"""
        try:
            gc.collect()
            logger.debug("執行記憶體清理")
        except Exception as e:
            logger.error(f"記憶體清理失敗: {e}")
    
    def should_cleanup_memory(self) -> bool:
        """檢查是否需要清理記憶體"""
        _, _, percent = self.get_memory_usage()
        return percent > self.memory_threshold
    
    def log_memory_status(self, context: str = "") -> None:
        """記錄記憶體使用狀況"""
        mem_mb, total_mb, percent = self.get_memory_usage()
        logger.info(f"{context} 記憶體使用: {mem_mb:.0f}MB/{total_mb:.0f}MB ({percent:.1f}%)")
        
        if percent > self.memory_threshold:
            logger.warning(f"記憶體使用率過高: {percent:.1f}%")
    
    def process_batch(self, image_files: List[str], **kwargs) -> Tuple[List[str], List[str]]:
        """
        處理一批圖片
        
        Args:
            image_files: 圖片文件路徑列表
            **kwargs: 傳遞給圖片處理的參數
            
        Returns:
            (成功處理的文件列表, 失敗的文件列表)
        """
        successful_files = []
        failed_files = []
        
        self.log_memory_status("批次處理開始前")
        
        for idx, image_file in enumerate(image_files):
            try:
                # 檢查記憶體使用率
                if self.should_cleanup_memory():
                    logger.info(f"記憶體使用率過高，執行清理...")
                    self.cleanup_memory()
                
                logger.info(f"處理圖片 {idx+1}/{len(image_files)}: {os.path.basename(image_file)}")
                
                # 處理單張圖片
                success, output_path = self.card_enhancer.process_image(image_file, **kwargs)
                
                if success:
                    successful_files.append(output_path)
                    logger.debug(f"成功處理: {os.path.basename(image_file)}")
                else:
                    failed_files.append(image_file)
                    logger.warning(f"處理失敗: {os.path.basename(image_file)}")
                
            except Exception as e:
                logger.error(f"處理圖片異常 {image_file}: {e}")
                failed_files.append(image_file)
        
        self.log_memory_status("批次處理完成後")
        
        # 最終清理
        self.cleanup_memory()
        
        return successful_files, failed_files
    
    def process_files_in_batches(self, all_files: List[str], **kwargs) -> Tuple[List[str], List[str]]:
        """
        將文件分批處理
        
        Args:
            all_files: 所有待處理文件列表
            **kwargs: 處理參數
            
        Returns:
            (所有成功文件列表, 所有失敗文件列表)
        """
        if not all_files:
            return [], []
        
        total_files = len(all_files)
        batches = [all_files[i:i + self.batch_size] for i in range(0, total_files, self.batch_size)]
        total_batches = len(batches)
        
        all_successful = []
        all_failed = []
        
        logger.info(f"開始批量處理: 共 {total_files} 個文件，分為 {total_batches} 批，每批 {self.batch_size} 個")
        
        for batch_idx, batch_files in enumerate(batches):
            logger.info(f"處理第 {batch_idx + 1}/{total_batches} 批")
            
            successful, failed = self.process_batch(batch_files, **kwargs)
            
            all_successful.extend(successful)
            all_failed.extend(failed)
            
            logger.info(f"第 {batch_idx + 1} 批完成: 成功 {len(successful)}/{len(batch_files)} 個")
        
        logger.info(f"批量處理完成: 總成功 {len(all_successful)}/{total_files} 個文件")
        
        return all_successful, all_failed
    
    def retry_failed_files(self, failed_files: List[str], **kwargs) -> Tuple[List[str], List[str]]:
        """
        重試失敗的文件，使用較小的批次大小
        
        Args:
            failed_files: 失敗的文件列表
            **kwargs: 處理參數
            
        Returns:
            (重試成功的文件列表, 仍然失敗的文件列表)
        """
        if not failed_files:
            return [], []
        
        logger.info(f"開始重試 {len(failed_files)} 個失敗的文件")
        
        # 使用較小的批次大小進行重試
        retry_batch_size = max(1, self.batch_size // 2)
        original_batch_size = self.batch_size
        self.batch_size = retry_batch_size
        
        try:
            successful, still_failed = self.process_files_in_batches(failed_files, **kwargs)
            logger.info(f"重試完成: 成功 {len(successful)}/{len(failed_files)} 個")
            return successful, still_failed
        finally:
            # 恢復原始批次大小
            self.batch_size = original_batch_size