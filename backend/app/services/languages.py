"""
Multi-language support for PDF extraction.

Supports 100+ languages for OCR via Docling/Surya.
"""

# Supported OCR languages (via Surya)
SUPPORTED_LANGUAGES = {
    # Major languages
    "en": "English",
    "es": "Spanish", 
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ms": "Malay",
    "tl": "Filipino/Tagalog",
    
    # European
    "nl": "Dutch",
    "pl": "Polish",
    "uk": "Ukrainian",
    "cs": "Czech",
    "el": "Greek",
    "hu": "Hungarian",
    "ro": "Romanian",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "tr": "Turkish",
    "he": "Hebrew",
    
    # South Asian
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
    
    # Others
    "fa": "Persian/Farsi",
    "sw": "Swahili",
    "am": "Amharic",
    "my": "Burmese",
    "km": "Khmer",
    "lo": "Lao",
    "ne": "Nepali",
    "si": "Sinhala",
}


def get_supported_languages() -> list[dict]:
    """Get list of supported languages for OCR."""
    return [
        {"code": code, "name": name}
        for code, name in sorted(SUPPORTED_LANGUAGES.items(), key=lambda x: x[1])
    ]


def detect_language(text: str) -> str:
    """
    Detect language of text.
    Returns language code.
    """
    try:
        from langdetect import detect
        return detect(text)
    except:
        return "en"  # Default to English


def is_rtl_language(lang_code: str) -> bool:
    """Check if language is right-to-left."""
    rtl_languages = {"ar", "he", "fa", "ur"}
    return lang_code in rtl_languages


def get_language_name(code: str) -> str:
    """Get full language name from code."""
    return SUPPORTED_LANGUAGES.get(code, code)
