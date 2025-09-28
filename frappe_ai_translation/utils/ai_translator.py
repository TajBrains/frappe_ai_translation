import os
import time
from typing import Dict, List, Optional

import frappe
from openai import OpenAI


class AITranslator:
    """AI-powered translator using OpenAI API"""
    
    def __init__(self, model: str = "gpt-4", api_key: Optional[str] = None):
        """
        Initialize AITranslator
        
        Args:
            model: OpenAI model to use (gpt-4, gpt-3.5-turbo, etc.)
            api_key: OpenAI API key. If not provided, looks for OPENAI_API_KEY env var
        """
        self.model = model
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            # Try to get from frappe config
            try:
                api_key = frappe.conf.get("openai_api_key")
            except:
                pass
            
        if not api_key:
            raise Exception("OpenAI API key is required. Set OPENAI_API_KEY environment variable or add 'openai_api_key' to site_config.json")
        
        self.client = OpenAI(api_key=api_key)
        
        # Rate limiting settings
        self.requests_per_minute = 60 if model.startswith("gpt-4") else 200
        self.last_request_time = 0
        self.request_interval = 60.0 / self.requests_per_minute

    def _rate_limit(self):
        """Simple rate limiting to avoid API limits"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def translate_batch(
        self, 
        strings: List[str], 
        source_lang: str = "en", 
        target_lang: str = "es",
        context: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Translate a batch of strings
        
        Args:
            strings: List of strings to translate
            source_lang: Source language code
            target_lang: Target language code  
            context: Additional context for translation
            
        Returns:
            Dictionary mapping original strings to translations
        """
        if not strings:
            return {}
            
        self._rate_limit()
        
        # Build the translation prompt
        prompt = self._build_translation_prompt(strings, source_lang, target_lang, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional translator specializing in software localization. You translate user interface text, error messages, and technical documentation with attention to context, tone, and cultural appropriateness."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent translations
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content
            return self._parse_translation_response(strings, result_text)
            
        except Exception as e:
            frappe.log_error(f"OpenAI translation error: {str(e)}")
            print(f"❌ Translation error: {str(e)}")
            return {}

    def _build_translation_prompt(
        self, 
        strings: List[str], 
        source_lang: str, 
        target_lang: str, 
        context: Optional[str]
    ) -> str:
        """Build the translation prompt for OpenAI"""
        
        # Language name mapping for better context
        lang_names = {
            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
            "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese",
            "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
            "th": "Thai", "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay",
            "tg": "Tajik", "uz": "Uzbek", "fa": "Persian", "ur": "Urdu"
        }
        
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)
        
        context_info = f"\n\nContext: This is for {context}" if context else ""
        context_info += "\n\nThis is software localization for an ERP system (Enterprise Resource Planning). Please ensure translations are:"
        context_info += "\n- Appropriate for business/professional context"
        context_info += "\n- Consistent with common ERP terminology"
        context_info += "\n- Natural and user-friendly"
        context_info += "\n- Preserve any technical terms, field names, or format specifiers (like {0}, %s, etc.)"
        
        # Format strings for the prompt
        numbered_strings = []
        for i, string in enumerate(strings, 1):
            # Escape the string to prevent prompt injection
            escaped = string.replace('"', '\\"').replace('\n', '\\n')
            numbered_strings.append(f'{i}. "{escaped}"')
        
        prompt = f"""Please translate these {source_name} strings to {target_name}.{context_info}

Strings to translate:
{chr(10).join(numbered_strings)}

Please respond with ONLY the translations in the following format (maintain the same numbering):
1. "translated string 1"
2. "translated string 2"
...

Important:
- Keep the same numbering format
- Preserve any HTML tags, placeholders like {{0}}, %s, etc.
- If a string cannot be translated, return it unchanged
- Maintain proper grammar and natural flow in {target_name}"""

        return prompt

    def _parse_translation_response(self, original_strings: List[str], response: str) -> Dict[str, str]:
        """Parse OpenAI response and map translations back to original strings"""
        translations = {}
        
        lines = response.strip().split('\n')
        
        for i, original in enumerate(original_strings):
            expected_prefix = f"{i + 1}. \""
            
            # Find the line that starts with this number
            translation = None
            for line in lines:
                line = line.strip()
                if line.startswith(expected_prefix):
                    # Extract the translation between quotes
                    try:
                        # Remove the number prefix and extract quoted content
                        content = line[len(expected_prefix):]
                        if content.endswith('"'):
                            translation = content[:-1]  # Remove trailing quote
                        else:
                            translation = content
                        break
                    except:
                        continue
            
            if translation:
                # Unescape the translation
                translation = translation.replace('\\"', '"').replace('\\n', '\n')
                translations[original] = translation
            else:
                print(f"⚠️  Could not parse translation for: {original[:50]}...")
                translations[original] = original  # Fallback to original
        
        return translations

    def translate_single(
        self, 
        text: str, 
        source_lang: str = "en", 
        target_lang: str = "es",
        context: Optional[str] = None
    ) -> str:
        """
        Translate a single string
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Additional context for translation
            
        Returns:
            Translated text
        """
        result = self.translate_batch([text], source_lang, target_lang, context)
        return result.get(text, text)

    def get_supported_languages(self) -> List[str]:
        """Get list of commonly supported language codes"""
        return [
            "af", "ar", "bg", "bn", "bs", "ca", "cs", "da", "de", "el",
            "en", "es", "et", "fa", "fi", "fr", "gu", "hi", "hr", "hu",
            "id", "is", "it", "ja", "ka", "kk", "ko", "lt", "lv", "mk",
            "ms", "mt", "nb", "nl", "pl", "pt", "ro", "ru", "sk", "sl",
            "sq", "sr", "sv", "sw", "ta", "te", "th", "tg", "tr", "uk",
            "ur", "uz", "vi", "zh"
        ]

    def detect_language(self, text: str) -> str:
        """
        Detect the language of given text
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected language code
        """
        self._rate_limit()
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheaper model for detection
                messages=[
                    {
                        "role": "system",
                        "content": "You are a language detection expert. Respond only with the ISO 639-1 language code (2 letters) of the given text."
                    },
                    {
                        "role": "user", 
                        "content": f"What language is this text: '{text}'"
                    }
                ],
                temperature=0,
                max_tokens=10
            )
            
            detected = response.choices[0].message.content.strip().lower()
            return detected if len(detected) == 2 else "en"
            
        except Exception as e:
            print(f"Language detection error: {str(e)}")
            return "en"  # Default to English
