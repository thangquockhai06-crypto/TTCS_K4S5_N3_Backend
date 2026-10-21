import csv
import io
from typing import List
from app.models.task import Task


class TaskExportService:
    @staticmethod
    def export_tasks_to_csv(tasks: List[Task]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Tiêu đề", "Trạng thái", "Hạn chót", "Người phụ trách", "Quá hạn"])
        for t in tasks:
            writer.writerow([
                t.id,
                t.title,
                t.status,
                t.due_date.isoformat() if t.due_date else "",
                t.assignee_id or "",
                "Có" if t.is_overdue else "Không",
            ])
        return output.getvalue()
