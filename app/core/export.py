"""
Tiện ích xuất file Excel (.xlsx) tương thích chuẩn HTTP StreamingResponse.
Tuân thủ PEP 8 và 100% Type Hints.
"""
import io
from typing import List, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from fastapi.responses import StreamingResponse


def export_to_excel(
    sheet_title: str,
    headers: List[str],
    rows: List[List[Any]],
    filename: str,
) -> StreamingResponse:
    """
    Sinh file Excel định dạng .xlsx từ dữ liệu đã được lọc theo data scope.
    """
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_title[:31]  # Giới hạn tiêu đề sheet của Excel

    # Thiết lập header với định dạng nổi bật
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")

    worksheet.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = worksheet.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    # Chèn dữ liệu dòng
    data_font = Font(name="Arial", size=10)
    for row_data in rows:
        worksheet.append(row_data)

    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.font = data_font

    # Tự động điều chỉnh độ rộng cột
    for col in worksheet.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
        worksheet.column_dimensions[column_letter].width = max(max_length + 4, 12)

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    response_headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=response_headers,
    )
