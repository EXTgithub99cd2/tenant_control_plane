from pathlib import Path
from zipfile import ZipFile
from xml.etree.ElementTree import iterparse

from openpyxl import load_workbook
from file_inspection.domain.models import DataSetInfo


class XlsxReader:
    def __init__(self, maximum_worksheets):
        self.maximum_worksheets = maximum_worksheets

    def supports(self, extension):
        return extension.lower() == ".xlsx"

    @staticmethod
    def _open_workbook(path):
        # Inbox objects are extensionless SHA-256 files. Supplying a binary
        # stream makes openpyxl inspect the OOXML package, not the suffix.
        stream = Path(path).open("rb")
        try:
            workbook = load_workbook(stream, read_only=True, data_only=True)
        except Exception:
            stream.close()
            raise
        return stream, workbook

    @staticmethod
    def _hidden_rows(path, worksheet):
        """Read hidden-row flags directly from worksheet XML.

        ReadOnlyWorksheet intentionally has no row_dimensions collection.
        Parsing only the row elements preserves streaming behavior and avoids
        loading the workbook a second time in normal mode.
        """
        hidden = set()
        worksheet_path = getattr(worksheet, "_worksheet_path", None)
        if not worksheet_path:
            return hidden
        try:
            with ZipFile(path) as package:
                with package.open(worksheet_path) as xml_stream:
                    for _, element in iterparse(xml_stream, events=("end",)):
                        if element.tag.endswith("}row"):
                            flag = str(element.attrib.get("hidden", "")).lower()
                            if flag in {"1", "true"}:
                                number = element.attrib.get("r")
                                if number and number.isdigit():
                                    hidden.add(int(number))
                            element.clear()
        except (KeyError, OSError, ValueError):
            # Hidden-row metadata is supplementary. A valid workbook remains
            # inspectable if this metadata cannot be read.
            return set()
        return hidden

    def list_datasets(self, path):
        stream, workbook = self._open_workbook(path)
        try:
            if len(workbook.worksheets) > self.maximum_worksheets:
                raise ValueError(
                    f"Workbook has more than {self.maximum_worksheets} worksheets"
                )
            return [
                DataSetInfo(
                    worksheet.title,
                    "worksheet",
                    worksheet.sheet_state == "visible",
                )
                for worksheet in workbook.worksheets
            ]
        finally:
            workbook.close()
            stream.close()

    def physical_rows(self, path, dataset, max_rows=None):
        stream, workbook = self._open_workbook(path)
        try:
            if not workbook.sheetnames:
                return [], {}
            name = dataset or workbook.sheetnames[0]
            if name not in workbook.sheetnames:
                raise ValueError(f"Worksheet not found: {name}")
            worksheet = workbook[name]
            hidden_rows = self._hidden_rows(path, worksheet)
            output = []
            for number, row in enumerate(
                worksheet.iter_rows(values_only=True), start=1
            ):
                values = list(row)
                is_blank = not any(
                    value is not None and str(value).strip() != ""
                    for value in values
                )
                output.append(
                    {
                        "source_row_number": number,
                        "values": values,
                        "is_blank": is_blank,
                        "is_hidden": number in hidden_rows,
                    }
                )
                if max_rows and len(output) >= max_rows:
                    break
            return output, {
                "worksheet": name,
                "worksheet_state": worksheet.sheet_state,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
            }
        finally:
            workbook.close()
            stream.close()

    def iter_rows(self, path, dataset, start, end=None):
        stream, workbook = self._open_workbook(path)
        try:
            if not workbook.sheetnames:
                return
            name = dataset or workbook.sheetnames[0]
            if name not in workbook.sheetnames:
                raise ValueError(f"Worksheet not found: {name}")
            worksheet = workbook[name]
            for number, row in enumerate(
                worksheet.iter_rows(values_only=True), start=1
            ):
                if number < start:
                    continue
                if end and number > end:
                    break
                yield number, list(row)
        finally:
            workbook.close()
            stream.close()

    def read(self, path, dataset, max_rows):
        rows, metadata = self.physical_rows(path, dataset, None)
        header = rows[0]["values"] if rows else []
        data_rows = [
            row["values"] for row in rows[1:] if not row["is_blank"]
        ]
        return {
            "headers": header,
            "rows": data_rows[:max_rows],
            "total_rows": sum(not row["is_blank"] for row in rows[1:]),
            "metadata": metadata,
            "physical_rows": rows,
        }
