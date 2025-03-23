import cv2
import face_recognition
import os
import numpy as np
import cvzone
import firebase_admin
from firebase_admin import firestore
from firebase_admin import db
from firebase_admin import storage


cap = cv2.VideoCapture(1)
cap.set(3, 1280)
cap.set(4, 720)


imgBackground = cv2.imread('Resources/background.png')

folderModePath = 'Resources/Modes'
modePathList = os.listdir(folderModePath)
imgModeList = []
for path in modePathList:
    imgModeList.append(cv2.imread(os.path.join(folderModePath, path)))

modeType = 0
counter = 0
id = -1

while True:
    success, img = cap.read()

    imgS = cv2.resize(img, (0,0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    faceCurFrame = face_recognition.face_locations(imgS)
    encodedFaceCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

    img = cv2.resize(img, (640, 480))
    imgModeList[0] = cv2.resize(imgModeList[0], (414, 633))
    imgBackground[162:162 + 480, 55:55+640] = img
    imgBackground[44:44 + 633, 808:808+414] = imgModeList[modeType]

#Cái encodedListKnown là biến của cái học sinh nha, cái này em đặt biến là gì thì em sửa lại


    for encodedFace, faceLoc in zip(encodedFaceCurFrame, faceCurFrame):
        matches = face_recognition.compare_faces(encodedListKnown, encodedFace)
        faceDistance = face_recognition.face_distance(encodedListKnown, encodedFace)

        matchIndex = np.argmin(faceDistance)

#studentIDs là cái mã của sinh viên

        if matches[matchIndex]:
            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x2 * 4
            bbox = (55 + x1, 162 + y1, x2 - x1 , y2 - y1)
            imgBackground = cvzone.cornerRect(imgBackground, bbox, rt = 0)
            id = studentIDs[matchIndex]

            if counter == 0:
                counter = 1
                modeType = 1

    if counter != 0:
        if counter == 1:
            studentInfo = db.reference(f'Students/{id}').get()


        cv2.putText(imgBackground, str(studentInfo['total_attendance']), (865,125),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 2)

    # cv2.imshow("Cam", img)
    cv2.imshow("Face-Attendance", imgBackground)
    cv2.waitKey(1)