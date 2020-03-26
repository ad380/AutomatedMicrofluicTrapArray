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
#['--video','/home/pi/python/ankitha-tests/2_e.mp4']q

# define the lower and upper boundaries of the "green"
# ball in the HSV color space, then initialize the
# list of tracked points
blueLower = (18, 28, 71)
blueUpper = (49, 255, 255)
pts = deque(maxlen=args["buffer"])

# grab the reference to the webcam and video writer
camera = Device()
camera.saveSnapshot('colorTest.jpg')
fourcc = cv2.cv.CV_FOURCC(*'MSVC')
out = cv2.VideoWriter('centerLeft_8psi_trial4.avi',fourcc, 10, (600,450)) 

#set trap location
trap = (538,224)

#set traps being used (solenoid number)
start = '1'
end = '3'

#allow warm up
time.sleep(1)

# keep looping
count = 1
currentCount = 0
switch = False
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

        # only proceed if at least one contour was found
        if len(cnts) > 0:
                # find the largest contour in the mask, then use
                # it to compute the minimum enclosing circle and
                # centroid
                c = max(cnts, key=cv2.contourArea)
                ((x, y), radius) = cv2.minEnclosingCircle(c)
                M = cv2.moments(c)
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

                #check location
                if center is not None:
                        ##if currentCount == 0 and (center[0])-trap[0] > -10:#center-center
                        if currentCount ==0 and (trap[0])-center[0] < 35:#center-left
                        ##if currentCount ==0 and (center[0])-trap[0] > 0 and (center[0])-trap[0] < 35:#center-right
                        ##if currentCount ==0 and trap[0]-(center[0]+radius) < 10:#right-left
                        ##if currentCount == 0 and (center[0]-radius)-trap[0] > 10:#left-right        
                                ser.write(end)
                                ser.write(start)
                                currentCount = count
                                switch = True
                                
                # only proceed if the radius meets a minimum size
                if radius > 10 and switch == False:
                        # draw the circle and centroid on the frame and trap,
                        # then update the list of tracked points
                        ##cv2.circle(frame, (int(x), int(y)), int(radius),(0, 255, 255), 2)
                        cv2.circle(frame, center, 5, (0, 0, 255), -1)

        # show trap location        
        ##cv2.circle(frame, trap, 5, (0,0, 255), -1)

        # update the points queue
        pts.appendleft(center)

        # loop over the set of tracked points
        for i in xrange(1, len(pts)):
                # if either of the tracked points are None, ignore
                # them
                if pts[i - 1] is None or pts[i] is None:
                    continue

                # otherwise, compute the thickness of the line and
                # draw the connecting lines
                thickness = int(np.sqrt(args["buffer"] / float(i + 1)) * 2.5)
                if switch == False:
                        cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)

        #release valves
        count += 1
        if count == 100:
                ser.write(end)
        elif count == 200:
                ser.write(start)
        elif count > 300 and currentCount>0 and count-currentCount>300:
                break

        # save and show the frame to our screen
        out.write(frame)
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        #if the 'q' key is pressed, stop the loop
        if key == ord("q"):
                ser.write(end)
                ser.write(start)
                break

# cleanup the camera and close any open windows
out.release()
cv2.destroyAllWindows()
