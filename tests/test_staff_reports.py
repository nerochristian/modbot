import unittest

from cogs.reports import Reports
from cogs.staff_reports import StaffReports


class StaffReportCommandTests(unittest.TestCase):
    def test_staff_report_group_does_not_collide_with_user_reports(self) -> None:
        self.assertEqual(Reports.report_group.name, "report")
        self.assertEqual(StaffReports.report_group.name, "staffreport")
        self.assertNotEqual(Reports.report_group.name, StaffReports.report_group.name)


if __name__ == "__main__":
    unittest.main()
