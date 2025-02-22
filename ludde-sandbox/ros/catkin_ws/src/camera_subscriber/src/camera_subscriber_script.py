#! /home/dat14lja/Desktop/Thesis/Vision-For-Robotic-RL/ludde-sandbox/venv/bin/python

import cv2
from cv_bridge import CvBridge, CvBridgeError
import numpy as np

import rospy
from sensor_msgs.msg import Image
from geometry_msgs.msg import PointStamped

from utils.ARHelper import ARHelper
from params_remote import *
from utils.photoshop import *

# Init
arhelper = ARHelper(marker_size_m)
with np.load(calibration_path) as X:
    intrinsic_camera, distortion, _, _ = [X[i] for i in ('camMatrix', 'distCoef', 'rVector', 'tVector')]

print("Camera Subscriber launched with parameters:")
print(intrinsic_camera, distortion)


# Finds ArUco:s in images and broadcast the 3D and 2D coordinates
class ArUcoFinder(object):
    world_points = []
    image_points = []
    corner_world_points = []
    corner_image_points = []

    def __init__(self):
        self.cv_bridge = CvBridge()
        self.subscriber = rospy.Subscriber('/camera/color/image_raw', Image, self.callback)

    def publish(self, camera_point):
        point = PointStamped()
        point.header.frame_id = 'camera_point'
        point.header.stamp = rospy.Time.now()
        point.point.x = camera_point[0]
        point.point.y = camera_point[1]
        point.point.z = camera_point[2]

    def callback(self, image):
        try:
            image = self.cv_bridge.imgmsg_to_cv2(image, desired_encoding="passthrough")

        except CvBridgeError as e:
            print(e)

        # Find ArUco Markers
        image, corners, ids = arhelper.find_markers(image)

        # Find Camera Coordinates
        for index in range(0, len(ids)):
            r_vec, t_vec, obj_corners = cv2.aruco.estimatePoseSingleMarkers(
                corners=corners,
                markerLength=marker_size_m,
                cameraMatrix=intrinsic_camera,
                distCoeffs=distortion)

            center_point = arhelper.find_center(corners[index], ids[index])
            camera_point = t_vec[index].flatten()
            self.image_points.append(center_point)
            self.world_points.append(camera_point)

        # Display Image
        cv2.imshow('image', image)
        cv2.waitKey(0)


def main():
    rospy.init_node('camera_subscriber_node')
    aruco_finder = ArUcoFinder()

    try:
        rospy.spin()
    except KeyboardInterrupt:
        print('Shutting down.')
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
