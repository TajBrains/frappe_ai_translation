# Frappe AI Translation

AI-powered translation system for Frappe/ERPNext applications. This app provides automated translation capabilities using OpenAI's GPT models, allowing you to quickly translate ERPNext and other Frappe apps into any language without waiting for Crowdin approval.

## ⚠️ **CRITICAL WARNING**

**🚨 DO NOT use `bench update-po-files` after using this AI translation workflow!**

The AI workflow consolidates translations from multiple apps into your target app. Using `bench update-po-files` will **overwrite and destroy** all your AI-generated translations because:

- `update-po-files` regenerates PO files from each app's individual POT file
- Your target app's POT file doesn't contain strings from other apps
- **Result**: All consolidated translations will be lost! 💸

### ✅ **Safe Commands After AI Translation:**

```bash
bench compile-po-to-mo --app your_target_app
bench build --app your_target_app
bench restart
```

### ❌ **Dangerous Commands (Will Destroy AI Translations):**

```bash
bench update-po-files --app your_target_app  # 🚨 DON'T USE!
bench generate-pot-file --app your_target_app  # 🚨 May cause issues
```

**Use only the AI workflow commands for updates:**

```bash
bench generate-pot-ai <locale> --app source_apps --output-app target_app
bench translate-ai <locale> --app target_app
```

## Features

🤖 **AI-Powered Translation**: Uses OpenAI GPT models for context-aware translations
📦 **Multi-App Consolidation**: Collect translatable strings from multiple apps into one target app
🧠 **Smart Translation Copy**: Automatically copies existing translations from source apps
🔄 **Incremental Updates**: Only adds missing strings, never overrides existing translations
🌍 **Multi-Language Support**: Support for 50+ languages
💾 **Batch Progress Saving**: Saves translation progress after each batch (interrupt-safe)
🎯 **Deduplication**: Smart handling of duplicate strings across apps

## Installation

1. **Clone this app to your Frappe bench:**

```bash
cd frappe-bench
bench get-app https://github.com/TajBrains/frappe_ai_translation.git
```

2. **Install dependencies:**

```bash
bench pip install openai babel
```

3. **Restart bench to register commands:**

```bash
bench restart
```

**Note:** This app works at the bench level and does **not** need to be installed on any site.

## Configuration

### OpenAI API Key

Add your OpenAI API key to your site configuration:

**Option 1: Environment Variable**

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

**Option 2: Common Site Config**

```bash
bench set-config openai_api_key "your-openai-api-key-here"
```

**Option 3: Manual common_site_config.json**
Edit `sites/common_site_config.json`:

```json
{
  "openai_api_key": "your-openai-api-key-here"
}
```

## Usage

The app provides a two-step workflow for AI translation:

### Step 1: Collect Translatable Strings

Collect translatable strings from multiple source apps into a single target app:

```bash
# Collect strings from multiple apps into target app
bench generate-pot-ai ru --app frappe --app erpnext --output-app tajerp

# Collect from all apps (except frappe_ai_translation) into target app
bench generate-pot-ai es --output-app custom_app

# Collect from specific app into same app
bench generate-pot-ai fr --app erpnext --output-app erpnext
```

This command:

- ✅ Extracts fresh translatable strings from source apps
- ✅ Copies existing translations from source apps (if they exist)
- ✅ Only adds missing strings - never overrides existing translations
- ✅ Safe to re-run after code updates to pick up new strings

### Step 2: AI Translation

Fill empty translations using OpenAI:

```bash
# Translate untranslated strings in target app
bench translate-ai ru --app tajerp

# Use specific OpenAI model
bench translate-ai es --app custom_app --model gpt-4o-mini

# Add context for better translations
bench translate-ai fr --app erpnext --context "ERP business management"

# Dry run to see what would be translated
bench translate-ai zh --app myapp --dry-run

# Overwrite existing translations (default: skip existing)
bench translate-ai pt --app myapp --overwrite-existing

# Custom batch size for API efficiency
bench translate-ai ru --app myapp --batch-size 10
```

The AI translator:

- ✅ Only translates empty/missing translations
- ✅ Preserves existing translations
- ✅ Saves progress after each batch (interrupt-safe)
- ✅ Works with standard Frappe translation files (PO format)

## Complete Workflow Example

Here's a complete example of translating ERPNext and Frappe into Russian, consolidating everything into your custom app:

```bash
# Step 1: Collect all translatable strings
bench generate-pot-ai ru --app frappe --app erpnext --output-app my_custom_app

# Step 2: Translate missing strings
bench translate-ai ru --app my_custom_app --model gpt-4o-mini --batch-size 50

# Step 3: Use standard Frappe commands to compile and apply
bench compile-po-to-mo --app my_custom_app
bench restart
```

## Advanced Examples

### Multiple Languages

```bash
# Set up for multiple languages
for lang in es fr de pt it; do
    echo "Setting up $lang..."
    bench generate-pot-ai $lang --app frappe --app erpnext --output-app my_app
    bench translate-ai $lang --app my_app
done
```

### Incremental Updates

```bash
# After code updates, safely add new strings
bench generate-pot-ai ru --app frappe --app erpnext --output-app my_app
# Only new strings will be added, existing translations preserved

# Translate only the new empty strings
bench translate-ai ru --app my_app
```

## Language Codes

Use standard ISO 639-1 language codes:

| Language | Code | Language   | Code | Language   | Code |
| -------- | ---- | ---------- | ---- | ---------- | ---- |
| English  | en   | Spanish    | es   | French     | fr   |
| German   | de   | Italian    | it   | Portuguese | pt   |
| Russian  | ru   | Chinese    | zh   | Japanese   | ja   |
| Korean   | ko   | Arabic     | ar   | Hindi      | hi   |
| Thai     | th   | Vietnamese | vi   | Indonesian | id   |
| Tajik    | tj   | Uzbek      | uz   | Persian    | fa   |

## Key Benefits

### 🎯 **Consolidation**

Instead of managing translations across multiple apps, consolidate everything into your custom app for easier management.

### 🧠 **Smart Updates**

The system intelligently:

- Copies existing translations from source apps
- Only adds missing strings
- Never overrides your manual translations
- Safe to re-run after code updates

### 💾 **Reliability**

- Batch processing saves progress after each batch
- Interrupt-safe - you can stop and resume anytime
- No conflicts with standard Frappe translation commands

### 🚀 **Performance**

- Efficient deduplication across apps
- Optimized batch sizes for API limits
- Progress tracking and ETA

## Integration with Frappe

This app provides an **alternative** to Frappe's standard translation workflow:

### **🔄 Traditional Workflow (Per-App)**

```bash
# Old way - manage each app separately
bench generate-pot-file --app erpnext
bench update-po-files --app erpnext
# Manual translation work...
bench compile-po-to-mo --app erpnext
bench build --app erpnext
```

### **🤖 AI Workflow (Consolidated)**

```bash
# New way - consolidate + AI translate
bench generate-pot-ai ru --app frappe --app erpnext --output-app my_app
bench translate-ai ru --app my_app
bench compile-po-to-mo --app my_app
bench build --app my_app
```

**Note:** With this AI workflow, you typically **don't need** `update-po-files` anymore since `generate-pot-ai` handles extracting and updating strings from multiple apps.

### No Site Parameter Required

All commands run at the bench level - no need for `--site` parameter:

```bash
# ✅ Simple bench-level commands
bench generate-pot-ai ru --app erpnext --output-app my_app
bench translate-ai ru --app my_app

# ❌ No need for site parameter
# bench --site mysite generate-pot-ai ...
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:

- Create an issue on GitHub
- Check the troubleshooting section
- Review Frappe translation documentation

---

**Note**: This tool generates machine translations that should be reviewed by native speakers before production use. AI translations are a starting point, not a replacement for human translation expertise.
