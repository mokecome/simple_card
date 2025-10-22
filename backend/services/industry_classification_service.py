"""
AI 产业分类服务

使用 OpenAI API 进行名片产业自动分类
"""

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from typing import Dict, List, Optional
import logging
from .task_manager import task_manager

logger = logging.getLogger(__name__)


class IndustryClassificationService:
    """AI 产业分类服务"""

    # 5个产业分类
    CATEGORIES = {
        1: "防詐",
        2: "旅宿",
        3: "工業應用",
        4: "食品業",
        5: "其他"
    }

    def __init__(self):
        """初始化 OpenAI 客户端（独立配置）"""
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.timeout = int(os.getenv("OPENAI_TIMEOUT", "30"))
        logger.info(f"初始化 AI 分类服务: model={self.model}, base_url={os.getenv('OPENAI_BASE_URL')}")

    def _build_prompt(self, company_name: str, position: str) -> str:
        """构建分类 Prompt"""
        return f"""公司名称: {company_name or '未提供'}
职位: {position or '未提供'}

请判断这家公司最可能属于以下哪个產業:
1. 防詐
2. 旅宿
3. 工業應用
4. 食品業
5. 其他

请用繁体中文回答，格式如下:
產業: [数字]
信心度: [0-100]"""

    def _parse_response(self, response_text: str) -> Dict[str, any]:
        """
        解析 AI 响应

        Args:
            response_text: AI 返回的文本

        Returns:
            包含 category, confidence, reason 的字典
        """
        try:
            logger.debug(f"解析 AI 响应: {response_text}")

            # 使用正则提取（兼容简繁体）
            category_match = re.search(r'[产產][业業][:：]\s*(\d+)', response_text)
            confidence_match = re.search(r'信心度[:：]\s*(\d+)', response_text)

            if not category_match:
                logger.warning("无法解析產業分类，使用默认值")
                raise ValueError("无法解析產業分类")

            category_num = int(category_match.group(1))
            if category_num not in self.CATEGORIES:
                logger.warning(f"产业编号 {category_num} 超出范围，默认为'其他'")
                category_num = 5  # 默认为"其他"

            confidence = int(confidence_match.group(1)) if confidence_match else 50

            result = {
                "category": self.CATEGORIES[category_num],
                "confidence": confidence,
                "reason": ""  # 不再需要理由
            }

            logger.info(f"分类结果: {result}")
            return result

        except Exception as e:
            logger.error(f"解析 AI 响应失败: {str(e)}")
            return {
                "category": "其他",
                "confidence": 0,
                "reason": ""
            }

    def classify_single(self, company_name: str, position: str) -> Dict[str, any]:
        """
        分类单张名片

        Args:
            company_name: 公司名称（中文或英文）
            position: 职位（中文或英文）

        Returns:
            包含 category, confidence, reason 的字典
        """
        try:
            prompt = self._build_prompt(company_name, position)
            logger.info(f"开始分类: 公司={company_name}, 职位={position}")

            # 调用 OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的产业分类专家。请使用繁体中文回答。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200,
                timeout=self.timeout
            )

            result_text = response.choices[0].message.content
            logger.debug(f"OpenAI 响应: {result_text}")

            return self._parse_response(result_text)

        except Exception as e:
            logger.error(f"AI 分类失败: {str(e)}")
            return {
                "category": "其他",
                "confidence": 0,
                "reason": ""
            }

    def classify_batch(self, cards: List[Dict]) -> List[Dict]:
        """
        批量分类名片

        Args:
            cards: 名片列表，每个名片包含 id, company_name_zh/en, position_zh/en

        Returns:
            分类结果列表
        """
        results = []
        total = len(cards)

        logger.info(f"开始批量分类 {total} 张名片")

        for index, card in enumerate(cards, 1):
            company = card.get('company_name_zh') or card.get('company_name_en') or ''
            position = card.get('position_zh') or card.get('position_en') or ''

            logger.info(f"[{index}/{total}] 分类名片 ID={card['id']}")

            classification = self.classify_single(company, position)

            results.append({
                "card_id": card['id'],
                "industry_category": classification['category'],
                "confidence": classification['confidence'],
                "reason": classification['reason'],
                "success": classification['confidence'] > 0
            })

        logger.info(f"批量分类完成: 总数={total}, 成功={sum(1 for r in results if r['success'])}")
        return results

    def classify_single_with_retry(self, card: Dict, max_retries: int = 3) -> Dict:
        """
        分类单张名片（带重试机制）

        Args:
            card: 名片数据
            max_retries: 最大重试次数

        Returns:
            分类结果
        """
        company = card.get('company_name_zh') or card.get('company_name_en') or ''
        position = card.get('position_zh') or card.get('position_en') or ''

        for attempt in range(max_retries):
            try:
                classification = self.classify_single(company, position)

                # 检查分类是否成功
                if classification['confidence'] > 0:
                    return {
                        "card_id": card['id'],
                        "industry_category": classification['category'],
                        "confidence": classification['confidence'],
                        "reason": classification['reason'],
                        "success": True
                    }

                # 置信度为0，重试
                if attempt < max_retries - 1:
                    logger.warning(f"名片 {card['id']} 分类置信度为0，重试 {attempt + 1}/{max_retries - 1}")
                    time.sleep(1)  # 短暂延迟后重试

            except Exception as e:
                logger.error(f"名片 {card['id']} 分类失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 失败后延迟更长时间
                else:
                    # 最后一次重试也失败，返回失败结果
                    return {
                        "card_id": card['id'],
                        "industry_category": "其他",
                        "confidence": 0,
                        "reason": "",
                        "success": False
                    }

        # 所有重试都失败
        return {
            "card_id": card['id'],
            "industry_category": "其他",
            "confidence": 0,
            "reason": "",
            "success": False
        }

    def classify_batch_async(self, cards: List[Dict], task_id: str) -> List[Dict]:
        """
        异步批量分类名片（多线程并发）

        Args:
            cards: 名片列表
            task_id: 任务ID

        Returns:
            分类结果列表
        """
        total = len(cards)
        logger.info(f"开始异步批量分类 {total} 张名片，任务ID: {task_id}")

        results = []
        max_workers = 5  # 5个并发线程

        def process_card(card):
            """处理单张名片"""
            # 检查任务是否被取消
            if task_manager.is_cancelled(task_id):
                logger.info(f"任务 {task_id} 已取消，停止处理名片 {card['id']}")
                return None

            # 分类名片（带重试）
            result = self.classify_single_with_retry(card, max_retries=3)

            # 更新进度
            task_manager.update_progress(task_id, success=result['success'])

            return result

        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_card = {executor.submit(process_card, card): card for card in cards}

            # 收集结果
            for future in as_completed(future_to_card):
                try:
                    result = future.result()
                    if result is not None:  # 未被取消
                        results.append(result)
                except Exception as e:
                    card = future_to_card[future]
                    logger.error(f"处理名片 {card['id']} 时发生异常: {str(e)}")
                    results.append({
                        "card_id": card['id'],
                        "industry_category": "其他",
                        "confidence": 0,
                        "reason": "",
                        "success": False
                    })
                    task_manager.update_progress(task_id, success=False)

        success_count = sum(1 for r in results if r['success'])
        logger.info(f"异步批量分类完成: 任务ID={task_id}, 总数={total}, 成功={success_count}, 失败={total - success_count}")

        return results
