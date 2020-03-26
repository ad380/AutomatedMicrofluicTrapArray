#ad380
# import the necessary packages
from collections import deque
import numpy as np
import argparse
import imutils
import cv2
import time
from VideoCapture import Device
import PIL
import serial

# set up arduino serial port
ser = serial.Serial('com4',9600)

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video",
	help="path to the (optional) video file")
ap.add_argument("-b", "--buffer", type=int, default=10,
	help="max buffer size")
args = vars(ap.parse_args())

# define the lower and upper boundaries of the "green"
# ball in the HSV color space, then initialize the
# list of tracked points
blueLower = (18, 28, 71)
blueUpper = (49, 255, 255)
pts = []

#grab a reference to the webcam and video writer
if not args.get("video", False):
        camera = Device()
        camera.saveSnapshot('colorTest.jpg')
        fourcc = cv2.cv.CV_FOURCC(*'MSVC')
        out = cv2.VideoWriter('visionTest6.avi',fourcc, 10, (600,450))

# otherwise, grab a reference to the video file
else:
        camera = cv2.VideoCapture(args["video"])

#set trap location
trap = (538,224)

#set traps being used
start = '1'
end = '3'

#allow warm up
time.sleep(1)

# keep looping
loopCount = 1
currentCount = 0
release = False
while True:
        # grab the current frame
        pil_img = camera.getImage()
        cv_img = cv2.cv.CreateImageHeader(pil_img.size,cv2.cv.IPL_DEPTH_8U, 3)
        cv2.cv.SetData(cv_img, pil_img.tobytes(), pil_img.size[0]*3)
        frame = np.asarray(cv_img[:,:])

        # resize the frame, blur it, and convert it to the HSV
        # color space
        frame = imutils.resize(frame, width=600)
        # blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # construct a mask for the color "green", then perform
        # a series of dilations and erosions to remove any small
        # blobs left in the mask
        mask = cv2.inRange(hsv, blueLower, blueUpper)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # find contours in the mask and initialize the current
        # (x, y) center of the ball
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[-2]
        center = None

        centers = []
        count = 0
        # only proceed if at least one contour was found
        for i in xrange(0,len(cnts)):
                # find the largest contour in the mask, then use
                # it to compute the minimum enclosing circle and
                # centroid
                c = cnts[i]
                ((x, y), radius) = cv2.minEnclosingCircle(c)
                M = cv2.moments(c)

                # only proceed if the radius meets a minimum size
                if radius > 15 and radius < 80:
                        # draw the circle and centroid on the frame,
                        # then update the list of tracked points
                        centers.append((int(M["m10"] / M["m00"]),int(M["m01"] / M["m00"])))
                        cv2.circle(frame, (int(x), int(y)), int(radius),(0, 255, 255), 2)
                        count+=1
        cv2.circle(frame, trap, 5, (0,0, 255), -1)
        ###centers.sort()
                        
        # update the points queue
        if len(centers)==0:
               pts = []
        if len(pts)<len(centers):
                pts = []
                while len(pts)<len(centers):
                        pts.append(deque(maxlen=args["buffer"]))
                for i in xrange(0,len(centers)):
                        pts[i].appendleft(centers[i])
        if len(pts)>len(centers):
                for i in xrange(0,len(pts)):
                        num = pts[i][0][0]
                        distance = 1000
                        index = 0
                        for j in xrange(0,len(centers)):
                                if abs(num-centers[j][0])<distance:
                                        distance = abs(num-centers[j][0])
                                        index = j
                        if abs(num-centers[index][0])<20:
                                pts[i].appendleft(centers[index])
                        else:
                                pts.pop(i)
                                break
        else: 
                for i in xrange(0,len(centers)):
                        num = pts[i][0][0]
                        distance = 1000
                        index = 0
                        for j in xrange(0,len(centers)):
                                if abs(num-centers[j][0])<distance:
                                        distance = abs(num-centers[j][0])
                                        index = j
                        pts[i].appendleft(centers[index])
                        centers.pop(index)
                        
        #check location
        if release == True and len(centers) > 0:
                if currentCount == 0 and (centers[0][0]+radius)-trap[0] > 20:
                        ser.write(end)
                        ser.write(start)
                        currentCount = loopCount
                        
        # loop over the set of tracked points
        for i in xrange(0, len(pts)):
                for j in xrange(1, len(pts[i])):
                        # if either of the tracked points are None, ignore
                        # them
                        if pts[i][j - 1] is None or pts[i][j] is None:
                            continue

                        # otherwise, compute the thickness of the line and
                        # draw the connecting lines
                        thickness = int(np.sqrt(args["buffer"] / float(j + 1)) * 2.5)
                        cv2.line(frame, pts[i][j - 1], pts[i][j], (0, 0, 255), thickness)
        #release valves
        loopCount += 1
        if count == 10:
                ser.write(end)
        elif count == 20:
                ser.write(end)
        elif count == 30:
                ser.write(end)
                ser.write(start)
                release = True
##        elif count == 500:
##                ser.write(start)
        elif count > 40 and currentCount>0 and count-currentCount>200:
                print 'fail'
                break

        # show the frame to our screen
        out.write(frame)
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        #if the 'q' key is pressed, stop the loop
        if key == ord("q"):
                ser.write(end)
                break

# cleanup the camera and close any open windows
out.release()
cv2.destroyAllWindows()
