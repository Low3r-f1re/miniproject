import os
import json
from typing import Optional, Dict, Any
from models import TranslationCache
from extensions import db

class TranslationService:
    """
    Translation Service - Using built-in fallback translations only
    Google Translate API has been removed to eliminate external dependencies
    """
    def __init__(self):
        pass

    def translate_text(self, text: str, target_lang: str, source_lang: str = 'auto') -> Optional[str]:
        """
        Translate text to target language with caching
        Uses built-in fallback translations only (Google Translate removed)
        """
        if not text or not target_lang:
            return text

        # Check cache first
        cached = TranslationCache.query.filter_by(
            source_text=text,
            source_lang=source_lang,
            target_lang=target_lang
        ).first()

        if cached:
            return cached.translated_text

        # Use fallback translation
        translated = self._fallback_translation(text, target_lang)

        if translated and translated != text:
            # Cache the result
            try:
                cache_entry = TranslationCache(
                    source_text=text,
                    translated_text=translated,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                db.session.add(cache_entry)
                db.session.commit()
            except Exception as e:
                print(f"Translation cache error: {e}")
                db.session.rollback()

        return translated or text

    def _fallback_translation(self, text: str, target_lang: str) -> str:
        """Basic fallback translation for common phrases"""
        translations = {
            'en': {
                'Hello': {'es': 'Hola', 'fr': 'Bonjour', 'de': 'Hallo', 'it': 'Ciao', 'pt': 'Olá'},
                'Thank you': {'es': 'Gracias', 'fr': 'Merci', 'de': 'Danke', 'it': 'Grazie', 'pt': 'Obrigado'},
                'Where is the bathroom?': {'es': '¿Dónde está el baño?', 'fr': 'Où sont les toilettes?', 'de': 'Wo ist die Toilette?', 'it': 'Dov\'è il bagno?', 'pt': 'Onde fica o banheiro?'},
                'How much does this cost?': {'es': '¿Cuánto cuesta esto?', 'fr': 'Combien ça coûte?', 'de': 'Wie viel kostet das?', 'it': 'Quanto costa questo?', 'pt': 'Quanto custa isso?'},
                'I need help': {'es': 'Necesito ayuda', 'fr': 'J\'ai besoin d\'aide', 'de': 'Ich brauche Hilfe', 'it': 'Ho bisogno di aiuto', 'pt': 'Preciso de ajuda'}
            }
        }

        # Simple lookup for common phrases
        if target_lang in ['es', 'fr', 'de', 'it', 'pt']:
            for phrase, trans in translations.get('en', {}).items():
                if phrase.lower() in text.lower():
                    return trans.get(target_lang, text)

        return text  # Return original text if no translation found

    def detect_language(self, text: str) -> str:
        """Detect the language of the given text (basic detection only)"""
        # Basic language detection - defaults to English
        # In a production app, you could integrate with open-source language detection libraries
        return 'en'

    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'ru': 'Russian',
            'th': 'Thai',
            'vi': 'Vietnamese'
        }

    def translate_restaurant_info(self, restaurant_data: Dict[str, Any], target_lang: str) -> Dict[str, Any]:
        """Translate restaurant information"""
        translated = restaurant_data.copy()

        fields_to_translate = ['name', 'description', 'cuisine_type', 'address']

        for field in fields_to_translate:
            if field in translated and translated[field]:
                translated[field] = self.translate_text(translated[field], target_lang)

        return translated

    def translate_activity_info(self, activity_data: Dict[str, Any], target_lang: str) -> Dict[str, Any]:
        """Translate activity information"""
        translated = activity_data.copy()

        fields_to_translate = ['title', 'description', 'category']

        for field in fields_to_translate:
            if field in translated and translated[field]:
                translated[field] = self.translate_text(translated[field], target_lang)

        return translated
