from django.core.management.base import BaseCommand
from django.db import transaction
from deep_translator import GoogleTranslator
from core.models import PoliticalParty, ElectedMember, ManifestoPoint, SubManifesto, Commitment, SubCommitment, Activity, Petition

class Command(BaseCommand):
    help = 'Translates missing English fields from Nepali using deep_translator'

    def handle(self, *args, **options):
        translator = GoogleTranslator(source='ne', target='en')
        
        models_to_translate = {
            PoliticalParty: ['name', 'description'],
            ElectedMember: ['name', 'constituency'],
            ManifestoPoint: ['title', 'description'],
            SubManifesto: ['title'],
            Commitment: ['title', 'description'],
            SubCommitment: ['title'],
            Activity: ['title', 'description'],
            Petition: ['title', 'description', 'target']
        }

        total_translated = 0

        for model, fields in models_to_translate.items():
            self.stdout.write(f"Processing model: {model.__name__}...")
            instances = model.objects.all()
            
            with transaction.atomic():
                for instance in instances:
                    updated = False
                    for field in fields:
                        ne_field = f"{field}_ne"
                        en_field = f"{field}_en"
                        
                        ne_val = getattr(instance, ne_field)
                        en_val = getattr(instance, en_field)
                        
                        if ne_val and not en_val:
                            try:
                                translated_text = translator.translate(ne_val)
                                setattr(instance, en_field, translated_text)
                                updated = True
                                total_translated += 1
                                self.stdout.write(self.style.SUCCESS(f"  Translated {model.__name__} (ID: {instance.pk}) {field}"))
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"  Failed translating {model.__name__} (ID: {instance.pk}) {field}: {str(e)}"))
                    
                    if updated:
                        instance.save()
        
        self.stdout.write(self.style.SUCCESS(f"\nDone! Successfully translated {total_translated} fields."))
