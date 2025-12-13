import re

RE_FREEBIE = re.compile(r"^\s*(комплекс)\s*$", re.IGNORECASE)
RE_CONTACT = re.compile(r"^\s*(контакт)\s*$", re.IGNORECASE)

RE_EMAIL = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+', re.IGNORECASE)
RE_NAME = re.compile(r'(?:имя|name):\s*([^;,\n\+\d@]+)', re.IGNORECASE)

# Телефон (поддержка разных форматов)
# Примеры: +77001234567, 87001234567, 8 700 123 45 67, +7 (700) 123-45-67
RE_PHONE = re.compile(
    r'(?:телефон|phone|тел|tel|номер)?\s*:?\s*'
    r'(\+?[78][\s\-]?'
    r'(?:\(?\d{3}\)?[\s\-]?)?'
    r'\d{3}[\s\-]?\d{2}[\s\-]?\d{2})',
    re.IGNORECASE
)

# Простой телефон в тексте (без префиксов)
RE_PHONE_SIMPLE = re.compile(
    r'[\+]?[78][\s\-]?'
    r'(?:\(?\d{3}\)?[\s\-]?)?'
    r'\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
)

def extract_phone(text: str) -> str | None:
    """Извлечение телефона из текста"""
    # Сначала пробуем с префиксом
    match = RE_PHONE.search(text)
    if match:
        phone = match.group(1) if match.lastindex else match.group(0)
        # Очищаем от пробелов и дефисов
        return ''.join(filter(lambda x: x.isdigit() or x == '+', phone))
    
    # Затем пробуем простой поиск
    match = RE_PHONE_SIMPLE.search(text)
    if match:
        phone = match.group(0)
        # Очищаем от пробелов и дефисов
        return ''.join(filter(lambda x: x.isdigit() or x == '+', phone))
    
    return None

def extract_name(text: str) -> str | None:
    """Извлечение имени из текста"""
    # Сначала пробуем найти после "Имя:"
    match = RE_NAME.search(text)
    if match:
        return match.group(1).strip()
    
    # Если нет явного указания "Имя:", пробуем извлечь первое слово
    # (только если в тексте нет email и телефона в начале)
    words = text.split()
    if words:
        first_word = words[0].strip(',.;:')
        # Проверяем, что это не email и не телефон
        if not RE_EMAIL.match(first_word) and not RE_PHONE_SIMPLE.match(first_word):
            # Проверяем, что это текст (буквы)
            if any(c.isalpha() for c in first_word):
                return first_word
    
    return None