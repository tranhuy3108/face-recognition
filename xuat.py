import csv
from datetime import datetime

def list_attendance_by_date(file_path):
    attendance = {}

    # Đọc dữ liệu từ file CSV
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date_str = row['date']
            name = row['name']
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if date not in attendance:
                attendance[date] = []
            attendance[date].append(name)

    # Hiển thị danh sách điểm danh theo ngày
    for date in sorted(attendance.keys(), reverse=True):
        print(f"{date}: {', '.join(attendance[date])}")

if __name__ == "__main__":
    list_attendance_by_date('attendance.csv')