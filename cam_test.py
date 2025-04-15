import cv2
import face_recognition
import numpy as np
import pyodbc
import datetime
import cvzone
import os

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
            self.imgBackground[44:44 + 633, 808:808 + 414] = cv2.resize(self.imgModeList[0], (414, 633))

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
                if self.counter == 1:
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

                        if not already_checked:
                            now = datetime.datetime.now()
                            self.cursor.execute("INSERT INTO Attendance (StudentID, Time, Status) VALUES (?, ?, ?)",
                                                self.id, now, 'Present')
                            self.conn.commit()
                            print(f"[✔] {self.StudentInfo['name']} đã điểm danh lúc {now.strftime('%Y-%m-%d %H:%M:%S')}")
                            cv2.putText(self.imgBackground, f"ID: {self.StudentInfo['id']}", (baseX, baseY),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                            cv2.putText(self.imgBackground, f"Ten: {self.StudentInfo['name']}", (baseX, baseY + lineHeight),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                            cv2.putText(self.imgBackground, "Trang thai: Da diem danh", (baseX, baseY + 2 * lineHeight),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 2)
                        else:
                            print(f"[⚠] {self.StudentInfo['name']} đã điểm danh hôm nay.")
                            cv2.putText(self.imgBackground, f"ID: {self.StudentInfo['id']}", (baseX, baseY),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                            cv2.putText(self.imgBackground, f"Ten: {self.StudentInfo['name']}", (baseX, baseY + lineHeight),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                            cv2.putText(self.imgBackground, "Trang thai: Da diem danh hom nay", (baseX, baseY + 2 * lineHeight),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)

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