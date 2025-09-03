"""
名片检测和图像增强模块
使用OpenCV实现名片四角检测、透视变换和图像优化
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List
import os
from PIL import Image


class CardDetector:
    """名片检测器：实现四角定位、透视变换和图像增强"""
    
    def __init__(self):
        self.min_card_area = 10000  # 最小名片面积
        self.target_width = 1200  # 目标输出宽度
        self.target_dpi = 300  # 目标DPI
        
    def detect_card_corners(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        检测名片的四个角点
        
        Args:
            image: 输入图像（numpy数组）
            
        Returns:
            四个角点坐标，失败返回None
        """
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 高斯模糊去噪
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Canny边缘检测
            edges = cv2.Canny(blurred, 50, 150)
            
            # 形态学操作，连接断开的边缘
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            edges = cv2.dilate(edges, kernel, iterations=1)
            
            # 查找轮廓
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # 找到最大的矩形轮廓
            max_area = 0
            best_contour = None
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < self.min_card_area:
                    continue
                    
                # 多边形逼近
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                # 寻找四边形
                if len(approx) == 4 and area > max_area:
                    max_area = area
                    best_contour = approx
            
            if best_contour is not None:
                # 重新排序角点（左上、右上、右下、左下）
                corners = self._order_points(best_contour.reshape(4, 2))
                return corners
            
            return None
            
        except Exception as e:
            print(f"角点检测失败: {e}")
            return None
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """
        将四个点按照左上、右上、右下、左下的顺序排列
        
        Args:
            pts: 四个点的坐标
            
        Returns:
            排序后的点坐标
        """
        rect = np.zeros((4, 2), dtype="float32")
        
        # 计算左上角和右下角
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # 左上角
        rect[2] = pts[np.argmax(s)]  # 右下角
        
        # 计算右上角和左下角
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # 右上角
        rect[3] = pts[np.argmax(diff)]  # 左下角
        
        return rect
    
    def perspective_transform(self, image: np.ndarray, corners: np.ndarray) -> np.ndarray:
        """
        执行透视变换，将倾斜的名片校正为正视图
        
        Args:
            image: 输入图像
            corners: 四个角点坐标
            
        Returns:
            变换后的图像
        """
        try:
            # 计算变换后的宽度和高度
            (tl, tr, br, bl) = corners
            
            # 计算新图像的宽度
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))
            
            # 计算新图像的高度
            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))
            
            # 标准名片宽高比约为1.75
            if maxWidth / maxHeight > 2.0 or maxWidth / maxHeight < 1.3:
                # 调整为标准比例
                if maxWidth / maxHeight > 1.75:
                    maxHeight = int(maxWidth / 1.75)
                else:
                    maxWidth = int(maxHeight * 1.75)
            
            # 定义目标点
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")
            
            # 计算透视变换矩阵
            M = cv2.getPerspectiveTransform(corners, dst)
            
            # 执行透视变换
            warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
            
            return warped
            
        except Exception as e:
            print(f"透视变换失败: {e}")
            return image
    
    def enhance_resolution(self, image: np.ndarray, target_width: Optional[int] = None) -> np.ndarray:
        """
        提升图像分辨率和质量
        
        Args:
            image: 输入图像
            target_width: 目标宽度（默认1200px）
            
        Returns:
            增强后的图像
        """
        try:
            if target_width is None:
                target_width = self.target_width
            
            # 获取当前尺寸
            height, width = image.shape[:2]
            
            # 计算放大比例
            if width < target_width:
                scale = target_width / width
                new_width = target_width
                new_height = int(height * scale)
                
                # 使用INTER_CUBIC进行高质量放大
                resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            else:
                resized = image
            
            # 图像增强
            enhanced = self._enhance_image(resized)
            
            return enhanced
            
        except Exception as e:
            print(f"分辨率提升失败: {e}")
            return image
    
    def _enhance_image(self, image: np.ndarray) -> np.ndarray:
        """
        图像增强处理：锐化、对比度调整、去噪
        
        Args:
            image: 输入图像
            
        Returns:
            增强后的图像
        """
        try:
            # 转换为LAB颜色空间
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 应用CLAHE（限制对比度自适应直方图均衡化）到L通道
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # 合并通道
            enhanced_lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            
            # 轻微锐化
            kernel = np.array([[-1, -1, -1],
                              [-1, 9, -1],
                              [-1, -1, -1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            
            # 混合原图和锐化图（避免过度锐化）
            result = cv2.addWeighted(enhanced, 0.7, sharpened, 0.3, 0)
            
            # 去噪
            result = cv2.bilateralFilter(result, 9, 75, 75)
            
            return result
            
        except Exception as e:
            print(f"图像增强失败: {e}")
            return image
    
    def process_card_image(self, image_path: str) -> Tuple[bool, str]:
        """
        完整的名片处理流程
        
        Args:
            image_path: 输入图像路径
            
        Returns:
            (成功标志, 处理后的图像路径或错误消息)
        """
        try:
            # 读取图像
            image = cv2.imread(image_path)
            if image is None:
                return False, "无法读取图像"
            
            # 检测名片角点
            corners = self.detect_card_corners(image)
            
            if corners is not None:
                # 执行透视变换
                transformed = self.perspective_transform(image, corners)
                print(f"成功检测并校正名片，原始尺寸: {image.shape[:2]}, 校正后: {transformed.shape[:2]}")
            else:
                # 如果检测失败，使用原图
                print("名片边缘检测失败，使用原图进行处理")
                transformed = image
            
            # 提升分辨率和增强图像
            enhanced = self.enhance_resolution(transformed)
            
            # 保存处理后的图像
            output_path = os.path.splitext(image_path)[0] + "_opencv_enhanced.jpg"
            
            # 转换为RGB（OpenCV使用BGR）
            enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
            
            # 使用PIL保存，设置高DPI
            pil_image = Image.fromarray(enhanced_rgb)
            pil_image.save(output_path, "JPEG", quality=95, dpi=(self.target_dpi, self.target_dpi))
            
            print(f"图像处理完成，输出尺寸: {enhanced.shape[:2]}, 保存路径: {output_path}")
            return True, output_path
            
        except Exception as e:
            error_msg = f"名片处理失败: {e}"
            print(error_msg)
            return False, error_msg
    
    def batch_process(self, image_paths: List[str]) -> List[Tuple[str, bool, str]]:
        """
        批量处理多张名片图像
        
        Args:
            image_paths: 图像路径列表
            
        Returns:
            处理结果列表 [(原路径, 成功标志, 新路径或错误消息)]
        """
        results = []
        for path in image_paths:
            success, result = self.process_card_image(path)
            results.append((path, success, result))
        return results


# 测试函数
if __name__ == "__main__":
    detector = CardDetector()
    
    # 测试单张图片
    test_image = "test_card.jpg"
    if os.path.exists(test_image):
        success, result = detector.process_card_image(test_image)
        if success:
            print(f"处理成功: {result}")
        else:
            print(f"处理失败: {result}")
    else:
        print(f"测试图片 {test_image} 不存在")