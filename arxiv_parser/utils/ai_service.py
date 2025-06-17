"""
AI服务封装模块
支持OpenAI格式的API调用（DeepSeek、OpenAI）和Ollama
"""

import json
import requests
from typing import Optional, Dict, Any
from ..config import AI_CONFIG
from .logger import setup_logger

logger = setup_logger("ai_service")

class AIService:
    """AI服务封装类"""
    
    def __init__(self):
        self.provider = AI_CONFIG["provider"]
        self.config = AI_CONFIG[self.provider]
        
    def judge_file_relevance(self, file_content: str, file_name: str, file_extension: str) -> bool:
        """
        判断文件是否与研究相关
        
        Args:
            file_content: 文件内容预览
            file_name: 文件名
            file_extension: 文件扩展名
            
        Returns:
            是否与研究相关（True表示保留，False表示丢弃）
        """
        prompt = self._build_file_judgment_prompt(file_content, file_name, file_extension)
        
        try:
            if self.provider in ["deepseek", "openai"]:
                response = self._call_openai_format_api(prompt)
            elif self.provider == "ollama":
                response = self._call_ollama_api(prompt)
            else:
                logger.warning(f"不支持的AI服务提供商: {self.provider}")
                return True  # 保守策略
            
            # 解析响应
            answer = response.strip().upper()
            if 'YES' in answer:
                logger.debug(f"AI判断保留文件: {file_name}")
                return True
            elif 'NO' in answer:
                logger.debug(f"AI判断丢弃文件: {file_name}")
                return False
            else:
                logger.warning(f"AI返回不明确答案 '{answer}'，保守保留文件: {file_name}")
                return True
                
        except Exception as e:
            logger.warning(f"调用AI判断文件 {file_name} 时出错: {e}，保守保留文件")
            return True
    
    def _build_file_judgment_prompt(self, file_content: str, file_name: str, file_extension: str) -> str:
        """构建文件判断提示词"""
        return f"""You are a file content analyzer for academic research papers. Your task is to determine if a file extracted from a LaTeX research paper package is valuable for research or training purposes.

File Information:
- File name: {file_name}
- File extension: {file_extension}
- Content preview (first 200 lines):

{file_content}

Instructions:
1. Analyze if this file contains:
   - Research code (algorithms, experiments, data processing)
   - Research data (datasets, results, measurements)  
   - Configuration files for experiments
   - Documentation related to research methodology
   - Tables, figures, or supplementary research materials

2. EXCLUDE files that are:
   - System/template files (LaTeX templates, style files)
   - Software configuration unrelated to research
   - Auto-generated files from software (Word, PowerPoint, etc.)
   - Generic documentation or readme files
   - File format metadata or structure files

3. Respond with ONLY "YES" if the file should be kept for research purposes, or "NO" if it should be discarded.

Answer (YES/NO):"""

    def _call_openai_format_api(self, prompt: str) -> str:
        """调用OpenAI格式的API（支持DeepSeek、OpenAI等）"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['api_key']}"
        }
        
        data = {
            "model": self.config["model"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config["temperature"],
            "max_tokens": self.config["max_tokens"]
        }
        
        response = requests.post(
            f"{self.config['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=self.config["timeout"]
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API调用失败，状态码: {response.status_code}, 响应: {response.text}")
    
    def _call_ollama_api(self, prompt: str) -> str:
        """调用Ollama API"""
        data = {
            "model": self.config["model"],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config["temperature"]
            }
        }
        
        response = requests.post(
            f"{self.config['base_url']}/api/generate",
            json=data,
            timeout=self.config["timeout"]
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        else:
            raise Exception(f"Ollama调用失败，状态码: {response.status_code}, 响应: {response.text}")

# 全局AI服务实例
ai_service = AIService() 