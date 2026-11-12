import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app


class TestEnrollmentSystem(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.secret_key = 'test_secret_key_enrollment'
        self.client = app.test_client()

    def test_01_fee_and_balance_calculation_logic(self):
        units, rate_per_unit, misc_fee, payment_made = 18, 500.00, 1500.00, 4000.00
        total_assessment = (units * rate_per_unit) + misc_fee
        remaining_balance = total_assessment - payment_made
        self.assertEqual(total_assessment, 10500.00)
        self.assertEqual(remaining_balance, 6500.00)

    def test_02_core_routes_registered(self):
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        expected_routes = {
            '/login', '/logout', '/students', '/courses',
            '/course_offerings', '/reports/student_enrollment',
            '/reports/enrollment_summary', '/system/health'
        }
        for route in expected_routes:
            self.assertIn(route, rules, f"Missing expected route: {route}")

    def test_03_custom_404_error_handler(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'
        response = self.client.get('/this-route-does-not-exist-xyz')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.data)

    def test_04_system_health_and_database_integration(self):
        response = self.client.get('/system/health')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload.get('status'), 'ok')
        self.assertEqual(payload.get('database'), 'connected')
        self.assertGreater(payload.get('tables_detected', 0), 0)

    def test_05_unauthenticated_access_redirects_to_login(self):
        response = self.client.get('/students', follow_redirects=False)
        self.assertIn(response.status_code, (301, 302))
        self.assertIn('/login', response.headers.get('Location', ''))

    def test_06_rbac_blocks_student_from_admin_routes(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 999
            sess['role'] = 'student'
            sess['student_id'] = 1

        for restricted_path in ['/admin/dashboard', '/students', '/courses', '/reports/enrollment_summary']:
            res = self.client.get(restricted_path)
            self.assertEqual(res.status_code, 403, f"Student should be blocked from {restricted_path}")

    def test_07_rbac_blocks_cross_student_data_access(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 999
            sess['role'] = 'student'
            sess['student_id'] = 1

        res = self.client.get('/student/999/soa')
        self.assertEqual(res.status_code, 403)

    def test_08_login_page_renders(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)

    def test_09_admin_workflow_pages_render(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        for path in ['/students', '/courses', '/reports/student_enrollment', '/reports/enrollment_summary']:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Admin failed to load {path}")

    def test_10_csv_export_endpoint(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        res = self.client.get('/export_students_csv')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res.content_type)


if __name__ == '__main__':
    unittest.main(verbosity=2)
