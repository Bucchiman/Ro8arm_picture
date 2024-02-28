import cv2 as cv
import numpy as np


def main():
    img = cv.imread("arm_tracking_raw.jpg", 0)
    img_inv = cv.bitwise_not(img)
    #lines = cv.HoughLinesP(img_inv, rho=1, theta=np.pi/360, threshold=80, minLineLength=300, maxLineGap=5) # OK
    lines = cv.HoughLinesP(img_inv, rho=1, theta=np.pi/360, threshold=80, minLineLength=200, maxLineGap=5) # OOOKKKK
    #lines = cv.HoughLinesP(img_inv, rho=1, theta=np.pi/360, threshold=80, minLineLength=150, maxLineGap=5) # ???
    #lines = cv.HoughLinesP(img_inv, rho=1, theta=np.pi/360, threshold=80, minLineLength=100, maxLineGap=5) # NG
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # 線を消す(白で線を引く)
        no_lines_img = cv.line(img, (x1,y1), (x2,y2), (255,255,255), 3)
        cv.imwrite("arm_tracking.jpg", no_lines_img)
        #cv.imshow("traking", no_lines_img)


if __name__ == "__main__":
    main()
