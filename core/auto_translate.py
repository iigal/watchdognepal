"""
Auto-translation utility for bilingual (Nepali↔English) model fields.

Uses deep_translator (Google Translate) to fill the missing language
column whenever one language is submitted.
"""
import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


def auto_translate_fields(instance, fields, source_lang, target_lang):
    """
    For each field name in *fields*, read the value from the source-language
    column and, if the target-language column is empty, translate and fill it.

    Parameters
    ----------
    instance : Model instance (must be saved or at least have PK)
    fields   : iterable of base field names, e.g. ('title', 'description')
    source_lang : str – the language the user typed in, e.g. 'ne'
    target_lang : str – the language to auto-fill, e.g. 'en'
    """
    src_suffix = f"_{source_lang}"
    tgt_suffix = f"_{target_lang}"
    updated = False

    for field in fields:
        src_attr = f"{field}{src_suffix}"
        tgt_attr = f"{field}{tgt_suffix}"

        src_value = getattr(instance, src_attr, None)
        tgt_value = getattr(instance, tgt_attr, None)

        if src_value and not tgt_value:
            try:
                translated = GoogleTranslator(
                    source=source_lang,
                    target=target_lang,
                ).translate(src_value)
                if translated:
                    setattr(instance, tgt_attr, translated)
                    updated = True
            except Exception as exc:
                logger.warning(
                    "Auto-translate %s→%s for %s.%s failed: %s",
                    source_lang, target_lang,
                    type(instance).__name__, field, exc,
                )

    if updated:
        instance.save()


def auto_translate_activity(activity):
    """
    Detect which language the user submitted in and translate
    title + description into the other language.

    Heuristic: if title_ne is filled and title_en is empty → user
    submitted in Nepali. Vice-versa if title_en is filled and
    title_ne is empty.
    """
    translatable_fields = ('title', 'description')

    if getattr(activity, 'title_ne', None) and not getattr(activity, 'title_en', None):
        # User submitted in Nepali → translate to English
        auto_translate_fields(activity, translatable_fields, 'ne', 'en')
    elif getattr(activity, 'title_en', None) and not getattr(activity, 'title_ne', None):
        # User submitted in English → translate to Nepali
        auto_translate_fields(activity, translatable_fields, 'en', 'ne')
