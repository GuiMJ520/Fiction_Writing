"""工具函数 - token 估算、文本处理"""


def estimate_tokens(text: str) -> int:
    """估算文本的 token 数
    中文约 1 字 ≈ 1.5 token，英文约 1 词 ≈ 1.3 token
    """
    if not text:
        return 0
    # 统计中文字符数
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # 非中文字符按英文词估算（约4字符=1词）
    non_chinese = len(text) - chinese_chars
    english_words = non_chinese / 4
    return int(chinese_chars * 1.5 + english_words * 1.3)


def count_words(text: str) -> int:
    """统计字数（中文按字，英文按词）"""
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # 英文按空格分词
    non_chinese = len(text) - chinese_chars
    # 简化：非中文字符按 4 字符 = 1 词
    english_words = non_chinese / 4
    return int(chinese_chars + english_words)


def truncate_text(text: str, max_chars: int = 200) -> str:
    """截断文本到指定字符数，末尾加省略号"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """从文本提取关键词（简单实现：提取中文人名/地名候选 + 高频词）
    后续可升级为分词库或向量检索
    """
    # 简单实现：提取2-4字的中文连续字符段
    keywords = []
    current = ""
    for c in text:
        if '\u4e00' <= c <= '\u9fff':
            current += c
        else:
            if 2 <= len(current) <= 4:
                keywords.append(current)
            current = ""
    if 2 <= len(current) <= 4:
        keywords.append(current)

    # 去重并保留顺序
    seen = set()
    unique = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique[:max_keywords]
