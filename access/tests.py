"""
Tests for clock-in: certificates, shifts, site assignment, capacity and double clock-in.

Put this file at access/tests.py.
Run locally:   python manage.py test access
CI runs it automatically with:  python manage.py test

Django creates a separate, empty test database and deletes it afterwards,
so your real data is never touched.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from ninja.testing import TestClient

from access.api import router
from accounts.models import CustomUser, Organisation, Role, Site, SiteLinks
from certifications.models import Certification, CertificationResponse
from core.token import create_access_token
from scheduling.models import Schedule, ScheduleLinks

PIN = "482913"


class ClockInTests(TestCase):
    def setUp(self):
        # one company with one site
        self.org = Organisation.objects.create(
            name="Test Construction", contact_email="test@siteflow.dev"
        )
        self.site = Site.objects.create(
            organisation=self.org, name="Test Site", hard_capacity=100
        )

        # the gate operator: a platform admin in the same company
        self.operator = CustomUser.objects.create_user(
            phone="+2348000000001",
            password="SiteFlow#2026",
            name="Gate Operator",
            organisation=self.org,
            is_platform_admin=True,
        )
        token = create_access_token(self.operator)
        self.headers = {"Authorization": f"Bearer {token}"}

        # a shift happening right now at the site
        now = timezone.now()
        self.shift = Schedule.objects.create(
            name="Current shift",
            organisation=self.org,
            site=self.site,
            created_by=self.operator,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=7),
        )

        # the main worker: a scaffolder, assigned to the site and the shift
        self.worker = self.make_worker("+2348000000002", "EMP-001", "Scaffolder")

        # a certificate type required for scaffolders
        self.height = self.make_type("Working at Height", "Scaffolder")

        self.client = TestClient(router)

    # ---------- helpers ----------

    def make_worker(self, phone, employee_id, trade, on_site=True, on_shift=True):
        worker = CustomUser.objects.create_user(
            phone=phone,
            password="SiteFlow#2026",
            name=f"Worker {employee_id}",
            organisation=self.org,
            employee_id=employee_id,
            trade=trade,
        )
        worker.set_pin(PIN)
        worker.save()
        if on_site:
            SiteLinks.objects.create(user=worker, site=self.site, roles=Role.WORKER)
        if on_shift:
            ScheduleLinks.objects.create(
                schedule=self.shift, user=worker, assigned_by=self.operator
            )
        return worker

    def make_type(self, name, required_for_trade, is_active=True):
        return Certification.objects.create(
            name=name,
            description="",
            organisation=self.org,
            created_by=self.operator,
            required_for_trade=required_for_trade,
            is_active=is_active,
        )

    def give_certificate(self, worker, cert_type, status, expires_in_days=365):
        return CertificationResponse.objects.create(
            name=worker,
            certification=cert_type,
            expiration_date=timezone.now() + timedelta(days=expires_in_days),
            type="Certificate",
            certificate_number="CERT-123",
            status=status,
        )

    def clock_in(self, worker):
        return self.client.post(
            "/clock-in",
            json={
                "site_id": str(self.site.id),
                "employee_id": worker.employee_id,
                "pin": PIN,
            },
            headers=self.headers,
        )

    # ---------- certificates ----------

    def test_1_missing_required_certificate_is_refused(self):
        response = self.clock_in(self.worker)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Working at Height", response.json()["message"])

    def test_2_pending_certificate_is_refused(self):
        self.give_certificate(self.worker, self.height, CertificationResponse.Status.PENDING)
        response = self.clock_in(self.worker)
        self.assertEqual(response.status_code, 403)

    def test_3_approved_certificate_is_admitted(self):
        self.give_certificate(self.worker, self.height, CertificationResponse.Status.APPROVED)
        response = self.clock_in(self.worker)
        self.assertEqual(response.status_code, 201)

    def test_4_expired_certificate_is_refused(self):
        self.give_certificate(
            self.worker, self.height, CertificationResponse.Status.APPROVED, expires_in_days=-1
        )
        response = self.clock_in(self.worker)
        self.assertEqual(response.status_code, 403)

    def test_5_rejected_certificate_is_refused(self):
        self.give_certificate(self.worker, self.height, CertificationResponse.Status.REJECTED)
        response = self.clock_in(self.worker)
        self.assertEqual(response.status_code, 403)

    def test_6_worker_with_no_trade_is_admitted(self):
        worker = self.make_worker("+2348000000003", "EMP-002", "")
        response = self.clock_in(worker)
        self.assertEqual(response.status_code, 201)

    def test_7_trade_with_no_requirements_is_admitted(self):
        worker = self.make_worker("+2348000000004", "EMP-003", "Electrician")
        response = self.clock_in(worker)
        self.assertEqual(response.status_code, 201)

    def test_8_missing_one_of_two_required_certificates_is_refused(self):
        first_aid = self.make_type("First Aid", "Scaffolder")
        self.give_certificate(self.worker, self.height, CertificationResponse.Status.APPROVED)
        response = self.clock_in(self.worker)
        self.assertEqual(response.status_code, 403)
        self.assertIn(first_aid.name, response.json()["message"])

    def test_9_trade_case_mismatch_skips_the_check_known_gap(self):
        # KNOWN GAP: "scaffolder" != "Scaffolder", so no requirement is found.
        # When you fix case matching, change the expected code to 403.
        worker = self.make_worker("+2348000000005", "EMP-004", "scaffolder")
        response = self.clock_in(worker)
        self.assertEqual(response.status_code, 201)

    def test_10_inactive_certificate_type_is_ignored(self):
        self.height.is_active = False
        self.height.save()
        response = self.clock_in(self.worker)
        self.assertEqual(response.status_code, 201)

    # ---------- the other gate rules ----------

    def test_11_no_shift_is_refused(self):
        worker = self.make_worker("+2348000000006", "EMP-005", "", on_shift=False)
        response = self.clock_in(worker)
        self.assertEqual(response.status_code, 403)
        self.assertIn("No shift", response.json()["message"])

    def test_12_not_assigned_to_site_is_refused(self):
        worker = self.make_worker("+2348000000007", "EMP-006", "", on_site=False)
        response = self.clock_in(worker)
        self.assertEqual(response.status_code, 403)
        self.assertIn("not assigned", response.json()["message"])

    def test_13_wrong_pin_is_refused(self):
        response = self.client.post(
            "/clock-in",
            json={
                "site_id": str(self.site.id),
                "employee_id": self.worker.employee_id,
                "pin": "111999",
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_14_already_clocked_in_is_refused(self):
        worker = self.make_worker("+2348000000008", "EMP-007", "")
        self.assertEqual(self.clock_in(worker).status_code, 201)
        response = self.clock_in(worker)
        self.assertEqual(response.status_code, 403)
        self.assertIn("already clocked in", response.json()["message"])

    def test_15_full_site_is_refused(self):
        self.site.hard_capacity = 1
        self.site.save()
        first = self.make_worker("+2348000000009", "EMP-008", "")
        second = self.make_worker("+2348000000010", "EMP-009", "")
        self.assertEqual(self.clock_in(first).status_code, 201)
        response = self.clock_in(second)
        self.assertEqual(response.status_code, 403)
        self.assertIn("full", response.json()["message"])