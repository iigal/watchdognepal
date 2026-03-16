from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import PoliticalParty, ElectedMember, Petition

class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        return ['home', 'party_list', 'elected_member_list', 'activities_list', 'petition_list', 'manifesto_list']

    def location(self, item):
        return reverse(item)

class PartySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return PoliticalParty.objects.all()

class MemberSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ElectedMember.objects.all()

class PetitionSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Petition.objects.filter(status='active')

    def lastmod(self, obj):
        return obj.updated_at
