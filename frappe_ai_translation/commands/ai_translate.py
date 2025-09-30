import json
import os
from pathlib import Path

import click
import frappe
from babel.messages.catalog import Catalog
from babel.messages.pofile import read_po, write_po
from frappe.gettext.translate import (
    get_catalog,
    get_locales,
    get_po_path,
    get_pot_path,
    new_catalog,
    new_po,
    write_catalog,
)

from ..utils.ai_translator import AITranslator


@click.command("generate-pot-ai", help="AI Translation: Generate PO file with strings from source apps")
@click.argument("target_locale", required=True)
@click.option("--app", multiple=True, help="Source apps to extract strings from (can be used multiple times)")
@click.option("--output-app", required=True, help="Target app where PO file should be created/updated")
def generate_pot_ai(target_locale: str, app: tuple = (), output_app: str = None):
    """Generate PO file in output app with translatable strings from source apps"""
    
    # Initialize frappe without site
    frappe.init("")
    
    from frappe.gettext.translate import generate_pot

    # Validate output app
    available_apps = frappe.get_all_apps(True)
    if output_app not in available_apps:
        click.echo(f"❌ Error: Output app '{output_app}' not found.")
        click.echo(f"Available apps: {', '.join(available_apps)}")
        return
    
    # Determine which source apps to process
    if app:
        # Use specified apps
        source_apps = list(app)
    else:
        # Default: all apps except frappe_ai_translation and output_app
        source_apps = [a for a in available_apps if a not in ['frappe_ai_translation']]
    
    click.echo(f"🎯 Source apps: {', '.join(source_apps)}")
    click.echo(f"📦 Output app: {output_app}")
    click.echo(f"🌍 Target language: {target_locale}")
    
    if not source_apps:
        click.echo("❌ No source apps to process")
        return
    
    # Get or create PO file for target locale in output app
    po_path = get_po_path(output_app, target_locale)
    if not po_path.exists():
        click.echo(f"Creating new PO file for locale '{target_locale}' in {output_app}")
        new_po(target_locale, output_app)
    
    output_po_catalog = get_catalog(output_app, target_locale)
    
    total_strings_added = 0
    
    for app_name in source_apps:
        click.echo(f"\n📱 Processing source app: {app_name}")
        
        # Generate POT file first to ensure we have latest strings
        generate_pot(app_name)
        source_pot_catalog = get_catalog(app_name)
        string_count = sum(1 for msg in source_pot_catalog if msg.id and msg.id.strip())
        click.echo(f"📝 Found {string_count} translatable strings")
        
        # Get source app's PO file if it exists for this locale
        source_po_path = get_po_path(app_name, target_locale)
        source_po_catalog = None
        if source_po_path.exists():
            source_po_catalog = get_catalog(app_name, target_locale)
        
        # Add strings from source app to output app's PO file
        strings_added = 0
        for message in source_pot_catalog:
            if not message.id or not message.id.strip():
                continue
            
            # Check if string exists in output PO file
            existing_translation = output_po_catalog.get(message.id)
            if not existing_translation:
                # Check if source app has existing translation
                translation_text = ""
                if source_po_catalog:
                    source_message = source_po_catalog.get(message.id)
                    if source_message and source_message.string and source_message.string.strip():
                        translation_text = source_message.string
                
                # Add with source translation (if available) or empty
                output_po_catalog.add(
                    message.id,
                    string=translation_text,
                    locations=[(f"{app_name}:{loc[0]}", loc[1]) for loc in message.locations],
                    auto_comments=message.auto_comments,
                    context=message.context
                )
                strings_added += 1
        
        click.echo(f"✅ Added {strings_added} strings from {app_name}")
        total_strings_added += strings_added
    
    # Save the combined PO file
    if total_strings_added > 0:
        po_path = write_catalog(output_app, output_po_catalog, target_locale)
        click.echo(f"\n✅ Added {total_strings_added} total strings to {po_path}")
    else:
        click.echo(f"\n✅ PO file already contains all strings from source apps")
    
    click.echo(f"\n🎉 PO file ready for translation! Use 'translate-ai {target_locale} --app {output_app}' to fill with AI translations.")


@click.command("translate-ai", help="AI Translation: Automatically translate strings using OpenAI")
@click.argument("target_locale", required=True)
@click.option("--app", required=True, help="App to translate")
@click.option("--source-locale", default="en", help="Source language code (default: en)")
@click.option("--model", default="gpt-4", help="OpenAI model to use for translation")
@click.option("--batch-size", default=50, help="Number of strings to translate in each batch")
@click.option("--dry-run", is_flag=True, help="Show what would be translated without making changes")
@click.option("--overwrite-existing", is_flag=True, help="Overwrite existing translations (default: skip existing)")
def translate_ai(
    target_locale: str,
    app: str,
    source_locale: str = "en",
    model: str = "gpt-4",
    batch_size: int = 50,
    dry_run: bool = False,
    overwrite_existing: bool = False
):
    """Automatically translate strings using OpenAI API"""
    
    # Initialize frappe without site
    frappe.init("")
    
    # Validate app
    available_apps = frappe.get_all_apps(True)
    if app not in available_apps:
        click.echo(f"❌ Error: App '{app}' not found.")
        click.echo(f"Available apps: {', '.join(available_apps)}")
        return
    
    translator = AITranslator(model=model)
    
    click.echo(f"🤖 Starting AI translation of '{app}' to '{target_locale}'")
    click.echo(f"📋 Model: {model}, Batch size: {batch_size}")
    
    if dry_run:
        click.echo("🔍 DRY RUN MODE - No changes will be made")
    
    # Get or create PO file for target locale in the app
    po_path = get_po_path(app, target_locale)
    if not po_path.exists():
        click.echo(f"Creating new PO file for locale '{target_locale}' in {app}")
        new_po(target_locale, app)
    
    po_catalog = get_catalog(app, target_locale)
    
    # Find untranslated strings in the app's PO file
    strings_to_translate = []
    for message in po_catalog:
        if not message.id or not message.id.strip():
            continue

        # Check if string needs translation
        has_translation = message.string and message.string.strip()

        # Add to translation list if not translated or if overwriting existing
        if not has_translation or overwrite_existing:
            strings_to_translate.append({
                'text': message.id,
                'context': message.context
            })

    total_strings = len(strings_to_translate)
    click.echo(f"📝 Found {total_strings} untranslated strings in {app}")

    if not strings_to_translate:
        click.echo(f"✅ No strings to translate in {app}")
        return

    click.echo(f"\n📊 Total: {total_strings} strings to translate in {app}")

    if dry_run:
        click.echo("Would translate:")
        for i, item in enumerate(strings_to_translate[:5], 1):
            text = item['text']
            context = f" (context: {item['context']})" if item['context'] else ""
            click.echo(f"  {i}. {text[:60]}...{context}")
        if len(strings_to_translate) > 5:
            click.echo(f"  ... and {total_strings - 5} more")
        return

    # Translate all strings in batches
    total_translated = 0
    total_batches = (total_strings + batch_size - 1) // batch_size

    for i in range(0, total_strings, batch_size):
        batch = strings_to_translate[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        click.echo(f"🔄 Translating batch {batch_num}/{total_batches} ({len(batch)} strings)...")

        try:
            translations = translator.translate_batch(
                batch, 
                source_lang=source_locale,
                target_lang=target_locale,
            )
            
            # Update PO catalog with translations
            batch_translated = 0
            for original, translated in translations.items():
                if translated:
                    # Find the message in catalog by iteration (po_catalog.get() doesn't work reliably)
                    message = None
                    for msg in po_catalog:
                        if msg.id == original:
                            message = msg
                            break
                    
                    if message is None:
                        click.echo(f"⚠️  Warning: Message '{original[:50]}...' not found in catalog, skipping")
                        continue
                    
                    # Set the translation
                    message.string = translated
                    total_translated += 1
                    batch_translated += 1
            
            # Save progress after each batch
            if batch_translated > 0:
                po_path = write_catalog(app, po_catalog, target_locale)
                click.echo(f"💾 Saved {batch_translated} translations to {po_path}")
        except Exception as e:
            click.echo(f"❌ Error translating batch {batch_num}: {str(e)}")
            continue
    if total_translated > 0:
        click.echo(f"✅ Completed! Translated {total_translated} strings in {app}")
        click.echo(f"📁 Final file: {po_path}")
    else:
        click.echo(f"⚠️  No successful translations")

    click.echo(f"\n🎉 AI translation completed!")


commands = [
    generate_pot_ai,
    translate_ai,
]
