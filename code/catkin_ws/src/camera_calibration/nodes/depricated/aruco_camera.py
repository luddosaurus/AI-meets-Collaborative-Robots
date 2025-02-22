#! /home/csproj_vision/PycharmProjects/Vision-For-Robotic-RL/venv3/bin/python
# /home/oskarlarsson/PycharmProjects/Vision-For-Robotic-RL/venv/bin/python
# /home/dat14lja/thesis/Vision-For-Robotic-RL/code/venv/bin/python
import math

# Standard
import numpy as np

# OpenCV
import cv2
from cv_bridge import CvBridge, CvBridgeError

# ROS
import rospy
from sensor_msgs.msg import Image
import tf2_msgs.msg
import geometry_msgs.msg
import tf.transformations as tf

# Local
from camera_calibration.utils.ARHelper import ARHelper
from camera_calibration.utils.TFPublish import TFPublish
from camera_calibration.utils.MeanHelper import MeanHelper
from camera_calibration.params.calibration import marker_size_m, calibration_path
from camera_calibration.utils.TypeConverter import TypeConverter
from camera_calibration.utils.ErrorEstimator import ErrorEstimator
from camera_calibration.utils.DaVinci import DaVinci

# Init

with np.load(calibration_path) as X:
    intrinsic_camera, distortion, _, _ = [X[i] for i in ('camMatrix', 'distCoef', 'rVector', 'tVector')]

print("ArUcoFinder launched with internal parameters:")
print(intrinsic_camera, distortion)


# Finds ArUco:s from images and broadcast the tf (ArUco to Camera)
class ArUcoFinder(object):

    def __init__(self, charuco_board_shape=None, charuco_marker_size=None,
                 charuco_square_size=None, dict_type=None):
        self.cv_bridge = CvBridge()

        # todo add depth here
        self.subscriber = rospy.Subscriber('/camera/color/image_raw', Image, self.callback)
        self.pub_aruco_tf = rospy.Publisher("/tf", tf2_msgs.msg.TFMessage, queue_size=10)
        self.transforms = {}
        self.use_charuco = True
        self.r_vecs = np.random.random((3, 1))
        self.t_vecs = np.random.random((3, 1))

        self.arHelper = ARHelper(charuco_board_shape=charuco_board_shape, charuco_marker_size=charuco_marker_size,
                                 charuco_square_size=charuco_square_size, dict_type=dict_type)

        self.transform_memory = []

    # Finds the ArUco:s location in the camera 3D space

    def charuco_callback(self, image):
        image, self.r_vecs, self.t_vecs = self.arHelper.estimate_charuco_pose(
            image=image,
            camera_matrix=intrinsic_camera,
            dist_coefficients=distortion)
        stamped_transform = TypeConverter.vectors_to_stamped_transform(self.t_vecs,
                                                                       TypeConverter.rotation_vector_to_quaternions(
                                                                           self.r_vecs), "charuco", "charuco_to_camera")

        if len(self.transform_memory) > 5:
            self.transform_memory = self.transform_memory[1:]
        self.transform_memory.append(stamped_transform)
        std = ErrorEstimator.calculate_stds(self.transform_memory)
        sum_std = np.sum(std[0]) + np.sum(std[1])
        # cv2.putText(image, f'{sum_std}', (10, image.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 0), 2,
        #             cv2.LINE_AA)
        DaVinci.draw_text(image=image, text=f'{sum_std}')

        # print(sum_std)
        # self.r_vecs[2] -= math.pi / 2
        # print("---\n", self.r_vecs, self.t_vecs, "\n---")
        self.inv_and_pub(
            # parent_name="charuco",
            parent_name="charuco",
            child_name="charuco_to_camera",
            rotation=self.r_vecs,
            translation=self.t_vecs)

        return image

    def aruco_callback(self, image):
        # Find ArUco Markers
        image, corners, ids = self.arHelperr.find_markers(image)

        # image = ARHelper.draw_vectors(image, corners, ids, intrinsic_camera, distortion)

        if ids is not None:

            # todo make sure it's the right id / marker_size (if we use different for table)

            # Find Camera Coordinates 3D

            r_vecs, t_vecs, obj_corners = cv2.aruco.estimatePoseSingleMarkers(
                corners=corners,
                markerLength=marker_size_m,
                cameraMatrix=intrinsic_camera,
                distCoeffs=distortion)

            # NEW
            self.arHelper.draw_vectors(image, intrinsic_camera, distortion, r_vecs, t_vecs)

            for aruco_id, rotation, translation, corner_points in zip(ids, r_vecs, t_vecs, corners):
                transform_name = f"aruco_to_camera_{aruco_id}"
                aruco_name = f"aruco_{aruco_id}"
                self.inv_and_pub(
                    parent_name=aruco_name,
                    child_name=transform_name,
                    rotation=rotation,
                    translation=translation
                )
        return image

    def inv_and_pub(self, parent_name, child_name, rotation, translation):
        # change to aruco to camera
        translation, rotation = TypeConverter.invert_transform(
            translation=translation,
            rotation=rotation)
        # rotation = TypeConverter.rotation_vector_to_quaternions(rotation)
        if parent_name in self.transforms.keys():
            self.transforms[parent_name].append((translation, rotation))
        else:
            self.transforms[parent_name] = [(translation, rotation)]

        if len(self.transforms[parent_name]) > 5:
            translation, rotation = self.create_average_transform(aruco_name=parent_name, parent_frame=parent_name,
                                                                  child_frame=child_name)
            if not np.isnan(translation).any() and not np.isnan(rotation).any():
                TFPublish.publish_transform(
                    publisher=self.pub_aruco_tf,
                    parent_name=parent_name,
                    child_name=child_name,
                    translation=translation,
                    rotation=rotation
                )
            self.transforms[parent_name] = self.transforms[parent_name][1:]

    def callback(self, image):
        try:
            image = self.cv_bridge.imgmsg_to_cv2(image, desired_encoding="bgr8")

        except CvBridgeError as e:
            print(e)
        if self.use_charuco:
            image = self.charuco_callback(image)
        else:
            image = self.aruco_callback(image)

        # # Display Image
        # cv2.imshow('image', cv2.resize(image, (int(image.shape[1] / 2), int(image.shape[0] / 2))))
        # # cv2.imshow('image', image)
        # cv2.waitKey(1)

    def create_average_transform(self, aruco_name, parent_frame, child_frame):
        transformations = list()
        for transform in self.transforms[aruco_name]:
            transformations.append(
                TypeConverter.vectors_to_stamped_transform(
                    translation=transform[0],
                    rotation=transform[1],
                    parent_frame=parent_frame,
                    child_frame=child_frame)
            )

        return MeanHelper.riemannian_mean(transformations)


def main():
    rospy.init_node('aruco_camera_node')

    board = 2

    if board == 0:
        big_charuco_finder = ArUcoFinder(charuco_board_shape=(9, 14), charuco_square_size=0.04,
                                         charuco_marker_size=0.031,
                                         dict_type=cv2.aruco.DICT_5X5_100)
    elif board == 1:
        medium_charuco_finder = ArUcoFinder(charuco_board_shape=(18, 29), charuco_square_size=0.01,
                                            charuco_marker_size=0.008,
                                            dict_type=cv2.aruco.DICT_5X5_1000)
    elif board == 2:
        small_charuco_finder = ArUcoFinder(charuco_board_shape=(7, 10), charuco_square_size=0.012,
                                           charuco_marker_size=0.008,
                                           dict_type=cv2.aruco.DICT_4X4_50)
    try:
        rospy.spin()
    except KeyboardInterrupt:
        print('Shutting down.')
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
