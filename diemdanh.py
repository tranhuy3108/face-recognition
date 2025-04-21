import datetime
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

# Tạo thư mục lưu file điểm danh nếu chưa có
def tao_thu_muc_diem_danh(savefolder):
    if not os.path.exists(savefolder):
        os.makedirs(savefolder)

def diemdanh(ten, savefolder):
    # Cấu hình thời gian
    ontime = datetime.time(8, 0, 0)
    vang = (datetime.datetime.combine(datetime.date.today(), ontime) + datetime.timedelta(hours=2)).time() #vang la 10h
    current = datetime.datetime.now()

    time_str = current.strftime("%H:%M:%S")
    date_str = current.strftime("%d-%m-%Y")
    full_date_str = current.strftime("%d/%m/%Y") 

    #xác định trạng thái
    if current.time() <= ontime:
        status = "Đúng giờ"
    elif ontime < current.time() < vang:
        status = "Trễ"
    else:
        status = "Vắng"

    #in ra màn hình
    print(f"Tên: {ten}")
    print(f"Thời gian điểm danh: {time_str}")
    print(f"Trạng thái: {status}")

    #tạo thư mục lưu file nếu chưa có 
    tao_thu_muc_diem_danh(savefolder)

    #ghi vào file theo ngày trong thư mục đã tạo
    ten_file = os.path.join(savefolder, f"diemdanh_{date_str}.txt")
    with open(ten_file, mode='a', encoding='utf-8') as file:
        file.write(f"[{full_date_str} {time_str}] Tên: {ten} | Trạng thái: {status}\n")


class MyHandler(FileSystemEventHandler):
    def __init__(self, thu_muc, savefolder):
        self.thu_muc = thu_muc 
        self.savefolder = savefolder

    def on_created(self, event):
        if not event.is_directory: #kiểm tra xem có phải là file không
            ten = os.path.splitext(os.path.basename(event.src_path))[0] 
            diemdanh(ten, savefolder) #gọi hàm điểm danh với tên file
            print(f"Đã điểm danh: {ten}")

def diemdanhtufilethumuc(thumuc, savefolder):
    event_handler = MyHandler(thumuc, savefolder)
    observer = Observer()
    observer.schedule(event_handler, path=thumuc, recursive=False) 
    observer.start()

    print(f"🔍 Đang điểm danh...") #kiểm tra xem thư mục có file nào được thêm vào không
    try:
        while True:
            time.sleep(1) #check thư mục mỗi giây
    except KeyboardInterrupt: #hủy chương trình khi có lệnh từ bàn phím
        observer.stop()
        print("🔴 Dừng giám sát thư mục.")
    observer.join()

# === CHẠY CHƯƠNG TRÌNH ===
thumuc = r"D:\python\doan\skibiditestestyesyes"  # Thư mục chứa file tên học sinh
savefolder = r"D:\python\doan\diemdanh_files"  # Thư mục lưu file điểm danh
diemdanhtufilethumuc(thumuc, savefolder)
