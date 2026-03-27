from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import PoliticalParty, ElectedMember, ManifestoPoint, SubManifesto, Activity

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

    def test_submit_activity_with_source(self):
        self.client.login(username='testuser', password='password')
        data = {
            'title': 'Test Activity',
            'description': 'Description',
            'party': self.party.id,
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

class SubManifestoTests(TestCase):
    def setUp(self):
        self.party = PoliticalParty.objects.create(
            name="Test Party", 
            in_government=True, 
            oath_date=timezone.now().date() - timedelta(days=10)
        )
        self.manifesto = ManifestoPoint.objects.create(
            title="Main Manifesto",
            description="Description",
            party=self.party,
            completion_days=30
        )
        self.sub1 = SubManifesto.objects.create(
            parent=self.manifesto,
            title="Sub 1"
        )
        self.sub2 = SubManifesto.objects.create(
            parent=self.manifesto,
            title="Sub 2",
            deadline=timezone.now().date() + timedelta(days=5)
        )

    def test_deadline_inheritance(self):
        # sub1 should inherit parent's calculated deadline (10 days ago + 30 days = 20 days from now)
        expected_deadline = self.party.oath_date + timedelta(days=30)
        self.assertEqual(self.sub1.effective_deadline, expected_deadline)
        self.assertTrue(self.sub1.is_inherited_deadline)
        
        # sub2 has its own deadline
        self.assertEqual(self.sub2.effective_deadline, timezone.now().date() + timedelta(days=5))
        self.assertFalse(self.sub2.is_inherited_deadline)

    def test_progress_calculation(self):
        # ManifestoPoint should now have sub_manifestos
        self.assertEqual(self.manifesto.progress_fraction, "0/2")
        self.assertEqual(self.manifesto.completion_percentage, 0)
        
        self.sub1.is_completed = True
        self.sub1.save()
        
        self.assertEqual(self.manifesto.progress_fraction, "1/2")
        self.assertEqual(self.manifesto.completion_percentage, 50)
        
        self.sub2.is_completed = True
        self.sub2.save()
        
        self.assertEqual(self.manifesto.progress_fraction, "2/2")
        self.assertEqual(self.manifesto.completion_percentage, 100)

    def test_overdue_logic(self):
        # Create an overdue manifesto
        old_party = PoliticalParty.objects.create(
            name="Old Party", 
            in_government=True, 
            oath_date=timezone.now().date() - timedelta(days=100)
        )
        overdue_manifesto = ManifestoPoint.objects.create(
            title="Overdue Manifesto",
            party=old_party,
            completion_days=10
        )
        # 100 days ago + 10 days = 90 days ago (overdue)
        self.assertTrue(overdue_manifesto.is_overdue)
        
        # Sub-manifesto inheritance of overdue
        sub_overdue = SubManifesto.objects.create(
            parent=overdue_manifesto,
            title="Sub Overdue"
        )
        self.assertTrue(sub_overdue.is_overdue)
        
        # Complete it
        sub_overdue.is_completed = True
        sub_overdue.save()
        self.assertFalse(sub_overdue.is_overdue)
