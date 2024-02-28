import cv2 as cv


def main():
    img_arm_tracking = cv.imread("arm_tracking.jpg", 0)
    ret, mask = cv.threshold(img_arm_tracking, 0, 255, cv.THRESH_OTSU)
    #mask_inv = cv.bitwise_not(mask)
    cv.imwrite("mask.jpg", mask)

    img_fuji = cv.imread("processing_images/fuji_01.jpg")
    overlap = cv.bitwise_and(img_fuji, img_fuji, mask=mask)
    #overlap_bg_src = cv.cvtColor(overlap, cv.COLOR_BGR2RGB)
    #blend = cv.addWeighted(img_fuji, 0.5, img_arm_tracking, 0.5, 0)
    # blendsrc = cv.cvtColor(blend, cv.COLOR_BGR2RGB)
    cv.imwrite("overlap.jpg", overlap)


if __name__ == "__main__":
    main()
