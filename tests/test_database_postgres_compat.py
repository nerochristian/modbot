import asyncio
import unittest

from database import PostgresCompatCursor, PostgresCompatRow


class PostgresCompatRowTests(unittest.TestCase):
    def test_row_supports_column_and_positional_access(self) -> None:
        row = PostgresCompatRow(message_id=101, channel_id=202, content="hello")

        self.assertEqual(row["message_id"], 101)
        self.assertEqual(row[0], 101)
        self.assertEqual(row[1], 202)
        self.assertEqual(row[-1], "hello")
        self.assertEqual(row.get("content"), "hello")

    def test_cursor_wraps_mapping_rows_without_losing_positions(self) -> None:
        cursor = PostgresCompatCursor([{"id": 7, "status": "ready"}], rowcount=1)
        row = asyncio.run(cursor.fetchone())

        self.assertIsInstance(row, PostgresCompatRow)
        self.assertEqual(row[0], 7)
        self.assertEqual(row["status"], "ready")


if __name__ == "__main__":
    unittest.main()
