import os
import time
from typing import Dict, List, Optional

import frappe
from openai import OpenAI


class AITranslator:
    """AI-powered translator using OpenAI API"""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        """
        Initialize AITranslator
        
        Args:
            model: OpenAI model to use (gpt-4o-mini, gpt-3.5-turbo, etc.)
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
        self.requests_per_minute = 60 if model.startswith("gpt-4o-mini") else 200
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
    ) -> Dict[str, str]:
        """
        Translate a batch of strings
        
        Args:
            strings: List of strings to translate
            source_lang: Source language code
            target_lang: Target language code  
            
        Returns:
            Dictionary mapping original strings to translations
        """
        if not strings:
            return {}
        
        # Extract text and contexts from the new format
        if isinstance(strings[0], dict):
            # New format: list of {'text': str, 'context': str}
            string_texts = [item['text'] for item in strings]
            string_contexts = [item.get('context', '') for item in strings]
        else:
            # Old format: list of strings (fallback)
            string_texts = strings
            string_contexts = ['' for _ in strings]
            
        self._rate_limit()
        
        # Build the translation prompt with contexts
        prompt = self._build_translation_prompt_with_contexts(string_texts, string_contexts, source_lang, target_lang)
        
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
            return self._parse_translation_response(string_texts, result_text)

        except Exception as e:
            frappe.log_error(f"OpenAI translation error: {str(e)}")
            print(f"❌ Translation error: {str(e)}")
            return {}

    def _build_translation_prompt_with_contexts(
        self, 
        strings: List[str], 
        contexts: List[str],
        source_lang: str, 
        target_lang: str
    ) -> str:
        """Build the translation prompt for OpenAI with individual contexts"""
        
        # Language name mapping for better context
        lang_names = {
            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
            "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese",
            "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
            "th": "Thai", "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay",
            "tj": "Tajik", "uz": "Uzbek", "fa": "Persian", "ur": "Urdu"
        }
        
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)
        
        context_info = "This is software localization for an ERP system. Each string has specific context about where/how it's used. Please:"
        context_info += "\n- Use the context to provide accurate, contextual translations"
        context_info += "\n- Keep translations appropriate for business/professional context"  
        context_info += "\n- Preserve any technical terms, placeholders like {0}, %s, etc."
        context_info += "\n- Make translations natural and user-friendly"
        
        # Format strings with their individual contexts
        numbered_strings = []
        for i, (string, context) in enumerate(zip(strings, contexts), 1):
            # Escape the string to prevent prompt injection
            escaped = string.replace('"', '\\"').replace('\n', '\\n')
            context_part = f" [Context: {context}]" if context else ""
            numbered_strings.append(f'{i}. "{escaped}"{context_part}')
        
        prompt = f"""Please translate these {source_name} strings to {target_name}. {context_info}

Strings to translate:
{chr(10).join(numbered_strings)}

Please respond with ONLY the translations in the following format (maintain the same numbering):
1. "translated string 1"
2. "translated string 2"
etc.

Important:
- Keep the same numbering format
- Preserve any HTML tags, placeholders like {{0}}, %s, etc.
- Use the context to provide accurate translations
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
