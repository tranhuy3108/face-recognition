import csv
import os
from datetime import datetime

class AttendanceReader:
    def __init__(self, attendance_folder="attendance"):
        self.attendance_folder = attendance_folder
        os.makedirs(self.attendance_folder, exist_ok=True)

    def read_attendance_file(self, date_str):
        """
        Đọc file điểm danh theo ngày (date_str định dạng 'YYYY-MM-DD')
        Trả về danh sách các bản ghi điểm danh hoặc danh sách rỗng nếu không tìm thấy file.
        """
        filename = os.path.join(self.attendance_folder, f"{date_str}.csv")
        if not os.path.exists(filename):
            print(f"[⚠] Không tìm thấy file điểm danh cho ngày {date_str}.")
            return []  # Trả về danh sách rỗng thay vì None

        records = []
        with open(filename, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                records.append(row)

        return records

    def list_attendance_files(self):
        """
        Trả về danh sách tất cả các file điểm danh đang có
        """
        return [file for file in os.listdir(self.attendance_folder) if file.endswith(".csv")]

    def read_all_attendance(self):
        """
        Đọc toàn bộ các file điểm danh và gom thành danh sách
        """
        all_records = []
        files = self.list_attendance_files()
        for file in files:
            date_str = file.replace(".csv", "")
            records = self.read_attendance_file(date_str)
            all_records.extend(records)
        return all_records

    def input_date(self):
        while True:
            date_str = input("Nhập ngày (YYYY-MM-DD) hoặc nhập 0 để dừng: ")
            if date_str == "0":
                print("Đã dừng nhập!!!")
                return None 
            
            try:
                # Thử parse ngày
                datetime.strptime(date_str, "%Y-%m-%d")
                return date_str  # Nếu hợp lệ, return luôn chuỗi
            except ValueError:
                print("❌ Sai định dạng. Vui lòng nhập lại (đúng định dạng YYYY-MM-DD).")

    def print_attendance(self, date_str):
        records_today = self.read_attendance_file(date_str)
        if records_today:  # Kiểm tra xem có dữ liệu hay không
            # In tiêu đề
            print(f"Danh sách điểm danh cho ngày {date_str}:")
            print(f"{'Thời gian':<15} {'ID':<10} {'Tên':<20} {'Trạng thái':<10}")
            print("-" * 59)
            # In các bản ghi
            for record in records_today:
                print(f"{record['Thời gian']:<15} {record['ID']:<10} {record['Tên']:<20} {record['Trạng thái']:<10}")
        else:
            print("Không có dữ liệu điểm danh cho ngày này.")
