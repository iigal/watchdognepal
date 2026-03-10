from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import PoliticalParty, ElectedMember, ManifestoPoint, Activity

class WatchdogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.party = PoliticalParty.objects.create(name="Test Party", description="Test Description", in_government=True, oath_date=timezone.now().date())
        self.member = ElectedMember.objects.create(name="Test Member", constituency="Kathmandu", party=self.party, oath_date=timezone.now().date() - timedelta(days=1))
        self.manifesto_point = ManifestoPoint.objects.create(
            title="Fix Roads", 
            description="Fix all roads", 
            party=self.party,
            deadline=timezone.now().date() + timedelta(days=5)
        )

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.manifesto_point, response.context['upcoming_deadlines'])

    def test_party_list_view(self):
        response = self.client.get(reverse('party_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.party, response.context['parties'])

    def test_party_detail_view(self):
        response = self.client.get(reverse('party_detail', args=[self.party.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['party'], self.party)

    def test_member_list_view(self):
        response = self.client.get(reverse('elected_member_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.member, response.context['members'])

    def test_submit_activity_invalid_source(self):
        self.client.login(username='testuser', password='password')
        data = {
            'title': 'Test Activity',
            'description': 'Description',
            'level': 'federal',
            'source_link': 'https://example.com'  # Invalid source link
        }
        response = self.client.post(reverse('submit_activity'), data)
        self.assertContains(response, 'The source link must be a verified government source')

    def test_submit_activity_valid_source(self):
        self.client.login(username='testuser', password='password')
        data = {
            'title': 'Test Activity',
            'description': 'Description',
            'level': 'federal',
            'manifesto_point': self.manifesto_point.id,
            'source_link': 'https://mof.gov.np/some-page'
        }
        response = self.client.post(reverse('submit_activity'), data)
        self.assertEqual(response.status_code, 302)  # Should redirect to home
        self.assertTrue(Activity.objects.filter(title='Test Activity').exists())

    def test_calculated_deadline_with_party_oath(self):
        point = ManifestoPoint.objects.create(
            title="Relative Point",
            party=self.party,
            completion_years=1,
            completion_months=6
        )
        from dateutil.relativedelta import relativedelta
        expected_deadline = self.party.oath_date + relativedelta(years=1, months=6)
        self.assertEqual(point.calculated_deadline, expected_deadline)
        
    def test_calculated_deadline_with_member_oath(self):
        point = ManifestoPoint.objects.create(
            title="Member Relative Point",
            elected_member=self.member,
            completion_days=100
        )
        from dateutil.relativedelta import relativedelta
        expected_deadline = self.member.oath_date + relativedelta(days=100)
        self.assertEqual(point.calculated_deadline, expected_deadline)
