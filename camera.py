import cv2
import face_recognition
import numpy as np
import pyodbc
import datetime
import cvzone
import os
import csv

class FaceAttendanceSystem:
    def __init__(self, db_connection, background_img_path, mode_folder_path, camera_url):
        self.conn = db_connection
        self.cursor = self.conn.cursor()

        self.imgBackground = cv2.imread(background_img_path)
        self.imgModeList = [cv2.imread(f'{mode_folder_path}/{path}') for path in os.listdir(mode_folder_path)]

        self.encodedListKnown, self.studentIDs = self.load_encoded_faces_from_db()
        self.cap = cv2.VideoCapture(camera_url)
        self.cap.set(3, 1280)
        self.cap.set(4, 720)

        self.modeType = 0
        self.counter = 0
        self.id = -1
        self.StudentInfo = {}

    def load_encoded_faces_from_db(self):
        encodedList = []
        studentIDs = []

        self.cursor.execute("SELECT StudentID, Image FROM StudentImages")
        for row in self.cursor.fetchall():
            emp_id, img_data = row
            if img_data:
                nparr = np.frombuffer(img_data, np.uint8)
                img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                face_encodings = face_recognition.face_encodings(img_np)
                if face_encodings:
                    encodedList.append(face_encodings[0])
                    studentIDs.append(emp_id)
        return encodedList, studentIDs

    def recognize_and_attend(self):
        while True:
            success, img = self.cap.read()
            if not success:
                print("Không thể mở webcam.")
                return

            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            faceCurFrame = face_recognition.face_locations(imgS)
            encodedFaceCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

            img = cv2.resize(img, (640, 480))
            self.imgBackground[162:162 + 480, 55:55 + 640] = img
            mode_img = cv2.resize(self.imgModeList[self.modeType], (414, 633))
            self.imgBackground[44:44 + 633, 808:808 + 414] = mode_img
        

            for encodedFace, faceLoc in zip(encodedFaceCurFrame, faceCurFrame):
                matches = face_recognition.compare_faces(self.encodedListKnown, encodedFace)
                faceDistance = face_recognition.face_distance(self.encodedListKnown, encodedFace)

                matchIndex = np.argmin(faceDistance)

                if faceDistance[matchIndex] < 0.6:
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    bbox = (55 + x1, 162 + y1, x2 - x1, y2 - y1)
                    self.imgBackground = cvzone.cornerRect(self.imgBackground, bbox, rt=0)

                    self.id = self.studentIDs[matchIndex]
                    if self.counter == 0:
                        self.counter = 1
                        self.modeType = 1

            if self.counter != 0:
                if 1 <= self.counter <= 100:
                    self.cursor.execute("SELECT * FROM Students WHERE StudentID = ?", self.id)
                    row = self.cursor.fetchone()
                    if row:
                        self.StudentInfo = {
                            'id': row[0],
                            'name': row[1]
                        }

                        # Kiểm tra đã điểm danh hôm nay chưa
                        self.cursor.execute("""
                            SELECT * FROM Attendance 
                            WHERE StudentID = ? 
                            AND CONVERT(date, Time) = CONVERT(date, GETDATE())
                        """, self.id)
                        already_checked = self.cursor.fetchone()

                        baseX = 820
                        baseY = 200
                        lineHeight = 40

                        current_time = datetime.datetime.now()
                        status = self.tinh_trang_diem_danh()

                        # === GHI FILE CSV TRONG FOLDER attendance ===
                        attendance_folder = "attendance"
                        os.makedirs(attendance_folder, exist_ok=True)
                        filename = os.path.join(attendance_folder, current_time.strftime("%Y-%m-%d") + ".csv")
                        log_entry = [current_time.strftime('%H:%M:%S'), self.StudentInfo['id'], self.StudentInfo['name'], status]

                        if not already_checked:
                            self.modeType = 1
                            self.cursor.execute("INSERT INTO Attendance (StudentID, Time, Status) VALUES (?, ?, ?)",
                                                self.id, current_time, 'Present')
                            self.conn.commit()
                            print(f"[✔] {self.StudentInfo['name']} đã điểm danh lúc {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

                            file_exists = os.path.isfile(filename)
                            with open(filename, mode='a', newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                if not file_exists:
                                    writer.writerow(["Thời gian", "ID", "Tên", "Trạng thái"])
                                writer.writerow(log_entry)
                            # === CHÈN ẢNH SINH VIÊN TỪ DATABASE ===
                            self.cursor.execute("SELECT Image FROM StudentImages WHERE StudentID = ?", self.StudentInfo['id'])
                            img_row = self.cursor.fetchone()
                            if img_row and img_row[0]:
                                nparr = np.frombuffer(img_row[0], np.uint8)
                                face_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                                face_img = cv2.resize(face_img, (220, 220))  # kích thước ảnh avatar
                                self.imgBackground[170:170 + 220, 905:905 + 220] = face_img
                            text_color = (255, 255, 255)
                            cv2.putText(self.imgBackground, f"{self.StudentInfo['id']}", (1010, 495),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
                            cv2.putText(self.imgBackground, f"{self.StudentInfo['name']}", (1010, 550),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
                        else:
                            self.modeType = 2

                self.counter += 1
                if self.counter > 20:
                    self.counter = 0
                    self.modeType = 0
                    self.StudentInfo = {}
                    cv2.waitKey(2000)

            cv2.imshow("Face-Attendance", self.imgBackground)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.cap.release()
        cv2.destroyAllWindows()

    def tinh_trang_diem_danh(self):
        current = datetime.datetime.now().time()
        ontime = datetime.time(8, 0, 0)
        vang = datetime.time(10, 0, 0)
        if current <= ontime:
            return "Đúng giờ"
        elif current < vang:
            return "Trễ"
        else:
            return "Vắng"
