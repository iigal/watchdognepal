from modeltranslation.translator import register, TranslationOptions
from .models import PoliticalParty, ElectedMember, ManifestoPoint, SubManifesto, Commitment, SubCommitment, Activity, Petition

@register(PoliticalParty)
class PoliticalPartyTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

@register(ElectedMember)
class ElectedMemberTranslationOptions(TranslationOptions):
    fields = ('name', 'constituency')

@register(ManifestoPoint)
class ManifestoPointTranslationOptions(TranslationOptions):
    fields = ('title', 'description')

@register(SubManifesto)
class SubManifestoTranslationOptions(TranslationOptions):
    fields = ('title',)

@register(Commitment)
class CommitmentTranslationOptions(TranslationOptions):
    fields = ('title', 'description')

@register(SubCommitment)
class SubCommitmentTranslationOptions(TranslationOptions):
    fields = ('title',)

@register(Activity)
class ActivityTranslationOptions(TranslationOptions):
    fields = ('title', 'description')

@register(Petition)
class PetitionTranslationOptions(TranslationOptions):
    fields = ('title', 'description', 'target')
