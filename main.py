import cv2
import os
from deepface import DeepFace
from datetime import datetime
import pyodbc
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from camera import FaceAttendanceSystem
from XuatDS import AttendanceReader

# =============== CẤU HÌNH ===============
CAMERA_URL = "192.168.1.70//4747"

# Kết nối SQL Server
conn = pyodbc.connect(
    'DRIVER={SQL Server};'
    'SERVER=DESKTOP-SNLFM41\\SQLEXPRESS;'
    'DATABASE=Face-recognition;'
    'Trusted_Connection=yes;'
)
cursor = conn.cursor()
cursor.execute('''
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Students' AND xtype='U')
CREATE TABLE Students (
    StudentID NVARCHAR(10) PRIMARY KEY,
    StudentName NVARCHAR(100)
);
''')

# Tạo lại bảng StudentImages
cursor.execute('''
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='StudentImages' AND xtype='U')
CREATE TABLE StudentImages (
    ImageID INT IDENTITY PRIMARY KEY,
    StudentID NVARCHAR(10),
    Image VARBINARY(MAX),
    FOREIGN KEY (StudentID) REFERENCES Students(StudentID)
);
''')

cursor.execute('''
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Attendance' AND xtype='U')
CREATE TABLE Attendance (
    AttendanceID INT IDENTITY PRIMARY KEY,
    StudentID NVARCHAR(10),
    Time DATETIME,
    Status NVARCHAR(50),
    FOREIGN KEY (StudentID) REFERENCES Students(StudentID)
);
''')

conn.commit()


# =============== HÀM HỖ TRỢ ===============
def generate_student_id():
    cursor.execute("SELECT StudentID FROM Students")
    rows = cursor.fetchall()
    existing_ids = [int(row[0][2:]) for row in rows]
    expected_ids = set(range(1, len(existing_ids) + 2))
    available_ids = expected_ids - set(existing_ids)
    
    if available_ids:
        new_id_number = min(available_ids)
    else:
        new_id_number = max(existing_ids) + 1
    
    return f"SV{new_id_number:03d}"

def is_face_duplicate(new_face_img):
    cursor.execute("SELECT Image FROM StudentImages")
    rows = cursor.fetchall()
    for row in rows:
        if row[0] is not None:
            nparr = np.frombuffer(row[0], np.uint8)
            existing_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            try:
                result = DeepFace.verify(new_face_img, existing_img, enforce_detection=False)
                if result['verified']:
                    return True
            except:
                pass
    return False

def is_face_valid_for_update(student_id, new_face_img):
    # Lấy ảnh cũ của sinh viên hiện tại
    cursor.execute("SELECT Image FROM StudentImages WHERE StudentID = ?", (student_id,))
    row = cursor.fetchone()
    old_img = None
    if row and row[0]:
        nparr = np.frombuffer(row[0], np.uint8)
        old_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Nếu có ảnh cũ, so sánh với ảnh mới → nếu giống thì cho phép
    if old_img is not None:
        try:
            result = DeepFace.verify(new_face_img, old_img, enforce_detection=False)
            if result['verified']:
                return True  # Ảnh mới giống ảnh cũ → được cập nhật
        except:
            pass

    # So sánh ảnh mới với các ảnh khác trong hệ thống (ngoại trừ chính sinh viên này)
    cursor.execute("SELECT StudentID, Image FROM StudentImages WHERE StudentID != ?", (student_id,))
    rows = cursor.fetchall()
    for sid, img_bytes in rows:
        if img_bytes:
            nparr = np.frombuffer(img_bytes, np.uint8)
            existing_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            try:
                result = DeepFace.verify(new_face_img, existing_img, enforce_detection=False)
                if result['verified']:
                    print(f"❌ Khuôn mặt trùng với sinh viên khác (ID: {sid})")
                    return False  # Trùng người khác
            except:
                pass

    return True

def save_student_to_db(student_id, name):
    cursor.execute("INSERT INTO Students (StudentID, StudentName) VALUES (?, ?)", student_id, name)
    conn.commit()

def save_student_image_to_db(student_id, img):
    _, buffer = cv2.imencode('.jpg', img)
    img_bytes = buffer.tobytes()
    cursor.execute("INSERT INTO StudentImages (StudentID, Image) VALUES (?, ?)", student_id, img_bytes)
    conn.commit()

def add_new_student():
    name = input("Nhập tên sinh viên mới: ")
    student_id = generate_student_id()
    print("Chọn phương thức thêm ảnh (1: ảnh có sẵn, 2: chụp từ camera)")
    method = input("Lựa chọn: ")
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    img = None

    if method == "1":
        root = tk.Tk()
        root.withdraw()
        root.call('wm', 'attributes', '.', '-topmost', '1')
        file_path = filedialog.askopenfilename(title="Chọn ảnh", filetypes=[["Image Files", "*.jpg *.png"]])
        root.destroy()
        if not file_path:
            print("❌ Không chọn ảnh nào.")
            return
        img = cv2.imread(file_path)

    elif method == "2":
        cap = cv2.VideoCapture(CAMERA_URL)
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Không mở được camera.")
                cap.release()
                return
            cv2.imshow("Chụp ảnh (Nhấn 's' để lưu, 'q' để thoát)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                img = frame.copy()
                break
            elif key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return
        cap.release()
        cv2.destroyAllWindows()

    if img is None:
        print("❌ Không có ảnh để thêm.")
        return

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    if len(faces) == 0:
        print("❌ Ảnh không rõ khuôn mặt.")
        return
    if is_face_duplicate(img):
        print("❌ Khuôn mặt đã tồn tại trong hệ thống.")
        return

    save_student_to_db(student_id, name)
    save_student_image_to_db(student_id, img)
    print(f"[✔] Đã thêm sinh viên mới: {name} - Mã: {student_id}")

def save_new_student_image_to_db(student_id, img):
    cursor.execute("SELECT Image FROM StudentImages WHERE StudentID=?", student_id)
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            if row[0] is not None:
                nparr = np.frombuffer(row[0], np.uint8)
                existing_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                try:
                    result = DeepFace.verify(img, existing_img, enforce_detection=False)
                    if result['verified']:
                        print("✔ Khuôn mặt trùng với ảnh cũ. Lưu ảnh mới.")
                        _, buffer = cv2.imencode('.jpg', img)
                        img_bytes = buffer.tobytes()
                        cursor.execute("INSERT INTO StudentImages (StudentID, Image) VALUES (?, ?)", student_id, img_bytes)
                        conn.commit()
                        print(f"[✔] Đã thêm ảnh sinh viên Mã: {student_id}")
                        return
                except Exception as e:
                    print(f"❌ Lỗi khi so sánh khuôn mặt: {e}")
                    continue

    print("❌ Khuôn mặt không trùng với ảnh cũ. Không lưu ảnh mới.")

def update_student_image(student_id):
    cursor.execute("SELECT * FROM Students WHERE StudentID=?", student_id)
    if not cursor.fetchone():
        print("❌ Mã sinh viên không tồn tại.")
        return

    print("Chọn phương thức thêm ảnh (1: ảnh có sẵn, 2: chụp từ camera)")
    method = input("Lựa chọn: ")
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    img = None
    if method == "1":
        root = tk.Tk()
        root.withdraw()
        root.call('wm', 'attributes', '.', '-topmost', '1')
        file_path = filedialog.askopenfilename(title="Chọn ảnh", filetypes=[["Image Files", "*.jpg *.png"]])
        root.destroy()
        if not file_path:
            print("❌ Không chọn ảnh nào.")
            return
        img = cv2.imread(file_path)

    elif method == "2":
        cap = cv2.VideoCapture(CAMERA_URL)
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Không mở được camera.")
                cap.release()
                return
            cv2.imshow("Chụp ảnh (Nhấn 's' để lưu, 'q' để thoát)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                img = frame.copy()
                break
            elif key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return
        cap.release()
        cv2.destroyAllWindows()

    if img is None:
        print("❌ Không có ảnh để thêm.")
        return

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    if len(faces) == 0:
        print("❌ Ảnh không rõ khuôn mặt.")
        return
    if not is_face_valid_for_update(student_id, img):
        print("❌ Ảnh mới không hợp lệ. Có thể trùng với sinh viên khác.")
        return
    save_new_student_image_to_db(student_id, img)

def delete_student():
    student_id = input("Nhập mã sinh viên cần xoá: ")
    cursor.execute("SELECT * FROM Students WHERE StudentID=?", student_id)
    if not cursor.fetchone():
        print("❌ Mã sinh viên không tồn tại.")
        return
    cursor.execute("DELETE FROM Attendance WHERE StudentID=?", student_id)
    cursor.execute("DELETE FROM StudentImages WHERE StudentID=?", student_id)
    cursor.execute("DELETE FROM Students WHERE StudentID=?", student_id)
    conn.commit()
    print("[✔] Sinh viên đã được xoá khỏi hệ thống.")

def delete_student_image_gui(student_id):
    def load_images():
        for widget in frame_images.winfo_children():
            widget.destroy()

        cursor.execute("SELECT ImageID, Image FROM StudentImages WHERE StudentID=?", student_id)
        images = cursor.fetchall()
        if not images:
            messagebox.showerror("Lỗi", "Không tìm thấy ảnh cho sinh viên này.")
            win.destroy()
            return

        if len(images) <= 1:
            messagebox.showinfo("Không thể xóa", "Sinh viên chỉ còn 1 ảnh. Không thể xóa thêm.")
            win.destroy()
            return

        for idx, (img_id, img_data) in enumerate(images):
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img).resize((120, 120))
            img_tk = ImageTk.PhotoImage(img_pil)

            lbl = tk.Label(frame_images, image=img_tk)
            lbl.image = img_tk
            lbl.grid(row=0, column=idx, padx=5, pady=5)

            btn = tk.Button(frame_images, text=f"Xóa ảnh {idx+1}", fg="red",
                            command=lambda iid=img_id: confirm_delete(iid))
            btn.grid(row=1, column=idx)

    def confirm_delete(img_id):
        result = messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa ảnh này không?")
        if result:
            cursor.execute("SELECT COUNT(*) FROM StudentImages WHERE StudentID=?", student_id)
            total = cursor.fetchone()[0]
            if total <= 1:
                messagebox.showinfo("Không thể xóa", "Sinh viên chỉ còn 1 ảnh. Không thể xóa.")
                return
            cursor.execute("DELETE FROM StudentImages WHERE ImageID=?", img_id)
            conn.commit()
            messagebox.showinfo("Thành công", "Đã xóa ảnh.")
            load_images()

    win = tk.Toplevel()
    win.title("Xóa ảnh sinh viên")
    win.geometry("700x300")

    label = tk.Label(win, text=f"Danh sách ảnh sinh viên {student_id}", font=("Arial", 12, "bold"))
    label.pack(pady=10)

    global frame_images
    frame_images = tk.Frame(win)
    frame_images.pack(pady=10)

    load_images()

def edit_student():
    student_id = input("Nhập mã sinh viên cần sửa: ")
    cursor.execute("SELECT * FROM Students WHERE StudentID=?", student_id)
    if not cursor.fetchone():
        print("❌ Mã sinh viên không tồn tại.")
        return

    print("1. Sửa tên sinh viên")
    print("2. Cập nhật thêm ảnh sinh viên")
    print("3. Xóa ảnh sinh viên cụ thể (giao diện)")
    choice = input("Chọn thao tác (1, 2 hoặc 3): ")
    
    if choice == "1":
        new_name = input("Nhập tên mới: ")
        cursor.execute("UPDATE Students SET StudentName=? WHERE StudentID=?", new_name, student_id)
        conn.commit()
        print("[✔] Đã cập nhật tên sinh viên.")
    elif choice == "2":
        update_student_image(student_id)
    elif choice == "3":
        delete_student_image_gui(student_id)
    else:
        print("Lựa chọn không hợp lệ.")

def save_attendance_to_db(student_id, time, status):
    cursor.execute("INSERT INTO Attendance (StudentID, Time, Status) VALUES (?, ?, ?)", student_id, time, status)
    conn.commit()

def main():
    while True:
        print("\n=== HỆ THỐNG ĐIỂM DANH KHUÔN MẶT ===")
        print("1. Thêm sinh viên mới")
        print("2. Sửa thông tin sinh viên")
        print("3. Xóa sinh viên")
        print("4. Điểm danh khuôn mặt")
        print("5. Xem danh sách điểm danh")
        print("0. Thoát")
        choice = input("Chọn chức năng: ")
        if choice == "1":
            add_new_student()
        elif choice == "2":
            edit_student()
        elif choice == "3":
            delete_student()
        elif choice == "4":
            attendance_system = FaceAttendanceSystem(
                db_connection=conn,
                background_img_path='img/Resources/background.png',
                mode_folder_path='img/Resources/Modes',
                camera_url="http://192.168.1.70:4747/video"
            )
            attendance_system.recognize_and_attend()
        elif choice == "5":
            reader = AttendanceReader()
            date = reader.input_date()
            if date:
                records_today = reader.print_attendance(date)
        elif choice == "0":
            break
        else:
            print("Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()
