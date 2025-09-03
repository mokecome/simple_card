#!/usr/bin/env python3
"""
测试OpenCV名片处理功能
"""

import os
import sys
import glob

# 添加路径以导入模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.card_detector import CardDetector
from PIL import Image


def test_single_image(image_path):
    """测试单张图片"""
    print(f"\n{'='*60}")
    print(f"测试图片: {image_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(image_path):
        print(f"❌ 文件不存在: {image_path}")
        return False
    
    # 获取原始图片信息
    try:
        img = Image.open(image_path)
        print(f"原始尺寸: {img.size}")
        print(f"原始DPI: {img.info.get('dpi', 'N/A')}")
        img.close()
    except Exception as e:
        print(f"无法读取原始图片信息: {e}")
    
    # 使用CardDetector处理
    detector = CardDetector()
    success, result = detector.process_card_image(image_path)
    
    if success:
        print(f"✅ 处理成功!")
        print(f"输出路径: {result}")
        
        # 获取处理后图片信息
        try:
            enhanced_img = Image.open(result)
            print(f"处理后尺寸: {enhanced_img.size}")
            print(f"处理后DPI: {enhanced_img.info.get('dpi', 'N/A')}")
            
            # 计算放大倍率
            scale_x = enhanced_img.size[0] / img.size[0] if img else 0
            scale_y = enhanced_img.size[1] / img.size[1] if img else 0
            print(f"放大倍率: {scale_x:.2f}x (宽), {scale_y:.2f}x (高)")
            
            enhanced_img.close()
        except Exception as e:
            print(f"无法读取处理后图片信息: {e}")
            
        return True
    else:
        print(f"❌ 处理失败: {result}")
        return False


def test_batch_images():
    """测试批量处理"""
    # 查找output目录下的示例图片
    image_dir = "output/card_images"
    
    if not os.path.exists(image_dir):
        print(f"❌ 目录不存在: {image_dir}")
        return
    
    # 获取前5张图片进行测试
    patterns = ["front_*.jpg", "back_*.jpg"]
    test_images = []
    
    for pattern in patterns:
        images = glob.glob(os.path.join(image_dir, pattern))
        test_images.extend(images[:3])  # 每种类型取3张
    
    if not test_images:
        print(f"❌ 在 {image_dir} 中没有找到测试图片")
        return
    
    print(f"\n准备测试 {len(test_images)} 张图片...")
    
    success_count = 0
    for image_path in test_images:
        if test_single_image(image_path):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"批量测试完成: {success_count}/{len(test_images)} 成功")
    print(f"{'='*60}")


def main():
    """主测试函数"""
    print("OpenCV名片处理功能测试")
    print("="*60)
    
    # 检查OpenCV是否已安装
    try:
        import cv2
        print(f"✅ OpenCV版本: {cv2.__version__}")
    except ImportError:
        print("❌ OpenCV未安装，请运行: pip install opencv-python")
        return
    
    # 测试单张特定图片（如果提供）
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        test_single_image(image_path)
    else:
        # 批量测试
        test_batch_images()
    
    print("\n测试完成!")


if __name__ == "__main__":
    main()