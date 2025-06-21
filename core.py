import json
from enum import Enum
from typing import Dict, List, Tuple, Optional

class LangFormat(Enum):
    """
    语言文件格式枚举
    
    值:
        JSON: JSON格式 (.json)
        LANG: LANG格式 (.lang)
    """
    JSON = "json"
    LANG = "lang"

class TextElement:
    """
    表示单个翻译条目
    
    属性:
        key (str): 翻译项的键
        original_text (str): 原文内容
        translated_text (str): 译文内容
        _changed (bool): 标记是否被修改过
    """
    
    def __init__(self, key: str, original_text: str, translated_text: str = ""):
        """
        初始化翻译条目
        
        参数:
            key: 翻译项的键
            original_text: 原文内容
            translated_text: 译文内容（默认为空）
        """
        self.key = key
        self.original_text = original_text
        self.translated_text = translated_text
        self._changed = False  # 标记是否被修改过

    @property
    def is_translated(self) -> bool:
        """检查条目是否已翻译"""
        return bool(self.translated_text.strip())

    @property
    def is_changed(self) -> bool:
        """检查条目是否被修改过"""
        return self._changed

    def set_translated_text(self, text: str) -> None:
        """
        设置译文内容
        
        参数:
            text: 要设置的译文文本
        """
        if text != self.translated_text:
            self.translated_text = text
            self._changed = True  # 标记为已修改

    def reset(self) -> None:
        """重置译文内容"""
        self.translated_text = ""
        self._changed = False  # 重置修改标记

    def __str__(self) -> str:
        """返回译文（如果已翻译）或原文（如果未翻译）"""
        return self.translated_text if self.is_translated else self.original_text


class LangFileParser:
    """语言文件解析器，支持.lang和.json格式"""
    
    @staticmethod
    def detect_format(text: str) -> LangFormat:
        """
        自动检测语言文件格式
        
        参数:
            text: 文件内容文本
            
        返回:
            LangFormat: 检测到的文件格式
            
        异常:
            ValueError: 如果无法识别文件格式
        """
        # 清理文本，移除BOM标记和空白字符
        text = text.lstrip("\ufeff").strip()
        if not text:
            raise ValueError("文件内容为空")

        # 尝试解析为JSON
        try:
            json_data = json.loads(text)
            # 检查是否是键值对格式
            if isinstance(json_data, dict) and all(isinstance(v, str) for v in json_data.values()):
                return LangFormat.JSON
        except json.JSONDecodeError:
            pass  # 不是JSON格式，继续尝试其他格式

        # 检查是否是LANG格式
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("//"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() and value.strip():
                        return LangFormat.LANG

        raise ValueError("无法识别的语言文件格式，请确保文件是有效的语言文件")

    @staticmethod
    def parse(text: str, format: LangFormat) -> Tuple[Dict[str, str], List[str]]:
        """
        解析语言文件，返回键值字典和保持原始顺序的键列表
        
        参数:
            text: 文件内容文本
            format: 文件格式
            
        返回:
            Tuple[Dict[str, str], List[str]]: (键值字典, 保持原始顺序的键列表)
            
        异常:
            ValueError: 如果解析失败或未找到有效条目
        """
        if format == LangFormat.LANG:
            return LangFileParser._parse_lang(text)
        elif format == LangFormat.JSON:
            return LangFileParser._parse_json(text)
        else:
            raise ValueError(f"不支持的格式: {format}")

    @staticmethod
    def _parse_lang(text: str) -> Tuple[Dict[str, str], List[str]]:
        """
        解析.lang格式文件
        
        参数:
            text: 文件内容文本
            
        返回:
            Tuple[Dict[str, str], List[str]]: (键值字典, 保持原始顺序的键列表)
            
        异常:
            ValueError: 如果未找到有效的翻译条目
        """
        result = {}
        keys = []  # 保持键的原始顺序

        for line in text.split("\n"):
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # 查找键值分隔符
            separator_index = line.find("=")
            if separator_index == -1:
                continue  # 没有等号的行跳过

            # 提取键和值
            key = line[:separator_index].strip()
            value = line[separator_index + 1 :].strip()

            # 确保键和值都不为空
            if key and value:
                # 避免重复键
                if key not in result:
                    keys.append(key)
                    result[key] = value

        if not result:
            raise ValueError("未找到有效的翻译条目")

        return result, keys

    @staticmethod
    def _parse_json(text: str) -> Tuple[Dict[str, str], List[str]]:
        """
        解析JSON格式文件
        
        参数:
            text: 文件内容文本
            
        返回:
            Tuple[Dict[str, str], List[str]]: (键值字典, 保持原始顺序的键列表)
            
        异常:
            ValueError: 如果JSON无效或未找到有效的翻译条目
        """
        result = {}
        keys = []  # 保持键的原始顺序

        try:
            json_data = json.loads(text)
            for key, value in json_data.items():
                # 只处理字符串值
                if isinstance(value, str):
                    keys.append(key)
                    result[key] = value

            if not result:
                raise ValueError("未找到有效的翻译条目")

            return result, keys
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式无效: {str(e)}") from e

    @staticmethod
    def generate_output(data: Dict[str, str], format: LangFormat, keys: Optional[List[str]] = None) -> str:
        """
        生成输出文件内容
        
        参数:
            data: 键值对字典
            format: 输出格式
            keys: 键的顺序列表（可选）
            
        返回:
            str: 生成的输出文本
            
        异常:
            ValueError: 如果格式不支持
        """
        if format == LangFormat.LANG:
            # LANG格式：键=值，每行一个
            lines = []
            for key in keys or data.keys():
                if key in data:
                    lines.append(f"{key}={data[key]}")
            return "\n".join(lines)
        
        elif format == LangFormat.JSON:
            # JSON格式：保持键的顺序
            if keys:
                # 保持原始键的顺序
                ordered_dict = {key: data[key] for key in keys if key in data}
                return json.dumps(ordered_dict, ensure_ascii=False, indent=4)
            else:
                return json.dumps(data, ensure_ascii=False, indent=4)
        
        else:
            raise ValueError(f"不支持的格式: {format}")


class ModDictionary:
    """
    模组翻译字典管理
    
    属性:
        mod_namespace (str): 模组命名空间
        format (LangFormat): 文件格式
        text_dictionary (Dict[str, TextElement]): 翻译条目字典
        keys (List[str]): 保持原始顺序的键列表
    """
    
    def __init__(self, mod_namespace: str):
        """
        初始化模组字典
        
        参数:
            mod_namespace: 模组命名空间
        """
        self.mod_namespace = mod_namespace
        self.format: Optional[LangFormat] = None
        self.text_dictionary: Dict[str, TextElement] = {}
        self.keys: List[str] = []

    def load_original_file(self, text: str) -> None:
        """
        加载原始语言文件
        
        参数:
            text: 文件内容文本
            
        异常:
            ValueError: 如果加载失败
        """
        try:
            # 检测文件格式
            self.format = LangFileParser.detect_format(text)
            
            # 解析文件内容
            result, self.keys = LangFileParser.parse(text, self.format)
            if not result:
                raise ValueError("未找到有效的翻译条目")
            
            # 清空现有字典并加载新条目
            self.text_dictionary.clear()
            for key in self.keys:
                self.text_dictionary[key] = TextElement(key, result[key])
        
        except Exception as e:
            raise ValueError(f"加载文件失败: {str(e)}") from e

    def load_translated_file(self, text: str) -> None:
        """
        加载已翻译的语言文件
        
        参数:
            text: 文件内容文本
            
        异常:
            ValueError: 如果加载失败或原始文件未加载
        """
        if not self.text_dictionary:
            raise ValueError("必须先加载原始文本才能加载翻译")
        
        if not self.format:
            raise ValueError("未知的文件格式")
        
        try:
            # 解析翻译文件
            result, _ = LangFileParser.parse(text, self.format)
            
            # 更新翻译条目
            for key, value in result.items():
                if key in self.text_dictionary:
                    self.text_dictionary[key].set_translated_text(value)
        
        except Exception as e:
            raise ValueError(f"加载翻译文件失败: {str(e)}") from e

    def export(self) -> str:
        """
        导出翻译后的文件内容
        
        返回:
            str: 导出的文件内容
            
        异常:
            ValueError: 如果文件格式未设置
        """
        if not self.format:
            raise ValueError("无法导出，文件格式未设置")
        
        # 准备输出字典
        output_dict = {}
        for key in self.keys:
            element = self.text_dictionary.get(key)
            if element:
                output_dict[key] = str(element)  # 使用__str__方法获取最终文本
        
        # 生成输出内容
        return LangFileParser.generate_output(output_dict, self.format, self.keys)