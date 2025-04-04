import datetime

def diemdanh():
    # Thời gian quy định để điểm danh
    ontime = datetime.time(8, 0, 0)  # Set h dua tren 24 gio (HH::MM:SS)
    # Cộng thêm 2 giờ vào thời gian quy định
    vang = (datetime.datetime.combine(datetime.date.today(), ontime) + datetime.timedelta(hours=2)).time()

    # Nhập tên người điểm danh
    ten = input("Nhập tên của bạn: ")

    # Lấy thời gian hiện tại
    current = datetime.datetime.now().time()

    # Kiểm tra trạng thái
    if current <= ontime:
        status = "Đúng giờ"

    elif ontime < current < vang:
        status = "Trễ"
    else:
        status = "Vắng"

    formatcurrent = current.strftime("%H:%M:%S")

    # In ra thông tin điểm danh
    print(f"Tên: {ten}")
    print(f"Thời gian điểm danh: {formatcurrent}")
    print(f"Trạng thái: {status}")

# Gọi hàm điểm danh
while True:
    diemdanh()