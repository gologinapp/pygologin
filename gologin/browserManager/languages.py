from typing import Dict, List, Optional, Any

MAIN_LOCALE_LIST = [
  'af', 'am', 'ar', 'as', 'az', 'be', 'bg', 'bn', 'bs', 'ca', 'cs', 'cy', 'da', 'de', 'el', 'en-GB',
  'es-419', 'fr', 'fr-CA', 'gl', 'gu', 'he', 'hi', 'hr', 'hu', 'hy', 'id', 'is', 'it', 'ja', 'ka', 'kk', 'km', 'kn', 'ko', 'ky', 'lo', 'lt', 'lv',
  'ml', 'mn', 'mr', 'ms', 'my', 'nb', 'ne', 'nl', 'or', 'pa', 'pl', 'pt-BR', 'pt-PT', 'ro', 'ru', 'si', 'sk', 'sl', 'sq', 'sr', 'sr-Latn', 'sv', 'sw',
  'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'vi', 'zh-CN', 'zh-HK', 'zh-TW', 'zu', 'es', 'en-US', 'mk',
]

def check_browser_lang(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    navigator = profile_data.get('navigator', {})
    language = navigator.get('language', 'en-US')
    
    lang_parts = language.split(',')[0].strip() if language else 'en-US'
    
    return {
        'accept_languages': lang_parts,
        'selected_languages': lang_parts,
        'app_locale': lang_parts.split('-')[0] if '-' in lang_parts else lang_parts,
        'forced_languages': [lang_parts.split('-')[0] if '-' in lang_parts else lang_parts]
    }

def get_main_language(lang_arr: List[str]) -> str:
    for lang in lang_arr:
        if lang in MAIN_LOCALE_LIST:
            return lang
        
        locale = lang.split('-')[0]
        if locale in MAIN_LOCALE_LIST:
            return locale
    
    return ''

def get_intl_profile_config(profile_data: Dict[str, Any], timezone_check_result: Dict[str, Any], auto_lang: bool) -> Dict[str, Any]:
    if not auto_lang:
        return check_browser_lang(profile_data)
    
    timezone_lang = ''
    timezone_country = timezone_check_result.get('country', '')
    languages = timezone_check_result.get('languages')
    
    if not languages:
        return check_browser_lang(profile_data)
    
    first_detected_lang_locale = languages.split(',')[0]
    timezone_lang = f"{first_detected_lang_locale}-{timezone_country}" if timezone_country else first_detected_lang_locale
    
    result_langs_arr = []
    
    if '-' in timezone_lang:
        lang, country = timezone_lang.split('-', 1)
        if country:
            result_langs_arr.append(f"{lang}-{country}")
    else:
        lang = timezone_lang
    
    result_langs_arr.append(lang)
    result_langs_arr.extend(['en-US', 'en'])
    
    result_langs_arr = list(dict.fromkeys(result_langs_arr))
    
    main_language = get_main_language(result_langs_arr)
    
    return {
        'accept_languages': ','.join(result_langs_arr),
        'selected_languages': ','.join(result_langs_arr),
        'app_locale': main_language,
        'forced_languages': [main_language]
    }
