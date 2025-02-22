import numpy as np
import rospy
import tf
import cv2
import pandas as pd
from scipy.spatial.transform import Rotation
from geometry_msgs.msg import TransformStamped, Vector3, Quaternion


class TypeConverter:

    # Invert vector from O to (translation, rotation)
    @staticmethod
    def invert_transform(translation, rotation, turn_into_quaternion=True):
        if len(rotation) == 4:
            rotation = tf.transformations.quaternion_matrix(rotation)
            rotation_mat = rotation[:3, :3]

            # rotation_mat, _ = cv2.Rodrigues(rotation_matrix)
            # print(rotation_matrix)
            # print(rotation_mat)

        else:
            rotation_mat, _ = cv2.Rodrigues(rotation)

        # Change frame from Camera to ArUco, to ArUco to Camera
        inv_rotation = np.transpose(rotation_mat)

        inv_translation = np.matmul(-inv_rotation, translation)

        q_normalized = TypeConverter.rotation_vector_to_quaternions(inv_rotation)

        if turn_into_quaternion:
            return inv_translation, q_normalized
        else:
            return inv_translation, inv_rotation

    @staticmethod
    def invert_stamped_transform(stamped_transform):

        transform = stamped_transform.transform
        translation = [transform.translation.x,
                       transform.translation.y,
                       transform.translation.z]
        rotation = [transform.rotation.x,
                    transform.rotation.y,
                    transform.rotation.z,
                    transform.rotation.w]
        rotation_xyz = tf.transformations.euler_from_quaternion(rotation)
        reversed_translation, reversed_rotation = TypeConverter.invert_transform(translation=translation,
                                                                                 rotation=rotation_xyz)

        return TypeConverter.vectors_to_stamped_transform(translation=reversed_translation, rotation=reversed_rotation,
                                                          parent_frame=stamped_transform.child_frame_id,
                                                          child_frame=stamped_transform.header.frame_id)

    @staticmethod
    def invert_transform_tf(trans, rot):
        transform = tf.transformations.concatenate_matrices(tf.transformations.translation_matrix(trans),
                                                            tf.transformations.quaternion_matrix(rot))
        inversed_transform = tf.transformations.inverse_matrix(transform)
        translation = tf.transformations.translation_from_matrix(inversed_transform)
        quaternion = tf.transformations.quaternion_from_matrix(inversed_transform)
        return TypeConverter.vectors_to_stamped_transform(translation, quaternion, child_frame='camera_estimate', parent_frame='charuco')

    @staticmethod
    def rotation_vector_to_quaternions(rotation_vector):
        # Embed the rotation matrix in a 4x4 transformation matrix for the quaternion

        rotation_matrix = np.eye(4)
        rotation_matrix[:3, :3], _ = cv2.Rodrigues(rotation_vector)
        # Convert to Quaternion
        quaternion = tf.transformations.quaternion_from_matrix(rotation_matrix)

        # Normalize the quaternion because it's important
        q_norm = np.linalg.norm(quaternion)
        q_normalized = quaternion / q_norm

        return q_normalized

    @staticmethod
    def quaternion_to_rotation_vector(quaternions):
        matrix = tf.transformations.quaternion_matrix(quaternions)
        r_vec = cv2.Rodrigues(matrix)
        return r_vec

    @staticmethod
    def rotation_vector_list_to_quaternions(rotation_vector_list):
        quaternion_list = [TypeConverter.rotation_vector_to_quaternions(rotation) for rotation in rotation_vector_list]
        return quaternion_list

    # --------------------------------------- Transform

    @staticmethod
    def transform_to_matrices(transforms):
        rotation_matrices = []
        translations = []
        for transform in transforms:
            # Get the translation and quaternion from the transform message
            translation = np.array([transform.transform.translation.x,
                                    transform.transform.translation.y,
                                    transform.transform.translation.z])
            quaternion = np.array([transform.transform.rotation.x,
                                   transform.transform.rotation.y,
                                   transform.transform.rotation.z,
                                   transform.transform.rotation.w])
            # Convert the quaternion to a rotation matrix
            rotation_matrix = tf.transformations.quaternion_matrix(quaternion)[:3, :3]
            # Append the rotation matrix and translation to the output lists
            rotation_matrices.append(rotation_matrix)
            translations.append(translation)
        return rotation_matrices, translations

    # (4x4) transformation matrix to stamped transform
    @staticmethod
    def matrix_to_stamped_transform(matrix, parent_frame, child_frame):
        stamp = rospy.Time.now()

        translation = Vector3()
        translation.x, translation.y, translation.z = matrix[:3, 3]

        # New
        q = TypeConverter.matrix_to_quaternion_vector(matrix)

        rotation = Quaternion()
        rotation.x, rotation.y, rotation.z, rotation.w = q

        # Old
        # rotation.x, rotation.y, rotation.z, rotation.w = tf.transformations.quaternion_from_matrix(matrix)

        stamped_transform = TransformStamped()
        stamped_transform.header.stamp = stamp
        stamped_transform.header.frame_id = parent_frame
        stamped_transform.child_frame_id = child_frame
        stamped_transform.transform.translation = translation
        stamped_transform.transform.rotation = rotation

        return stamped_transform

    @staticmethod
    def matrix_to_quaternion_vector(matrix):

        embedded_rotation = np.eye(4)
        embedded_rotation[:3, :3] = matrix

        q = tf.transformations.quaternion_from_matrix(embedded_rotation)
        q_norm = np.linalg.norm(q)
        q = q / q_norm

        return q

    @staticmethod
    def extract_translation_rotation(transform):
        # Extract the translation components
        translation = np.array([
            transform.transform.translation.x,
            transform.transform.translation.y,
            transform.transform.translation.z
        ])

        # Extract the rotation components
        rotation = np.array([
            transform.transform.rotation.x,
            transform.transform.rotation.y,
            transform.transform.rotation.z,
            transform.transform.rotation.w
        ])

        return translation, rotation

    @staticmethod
    def vectors_to_stamped_transform(translation, rotation, parent_frame, child_frame):

        stamp = rospy.Time.now()

        tvec = Vector3()
        if translation is not None:
            tvec.x, tvec.y, tvec.z = translation.flatten()
        else:
            tvec.x, tvec.y, tvec.z = 0, 0, 0

        rvec = Quaternion()
        rvec.x, rvec.y, rvec.z, rvec.w \
            = rotation

        stamped_transform = TransformStamped()
        stamped_transform.header.stamp = stamp
        stamped_transform.header.frame_id = parent_frame
        stamped_transform.child_frame_id = child_frame
        stamped_transform.transform.translation = tvec
        stamped_transform.transform.rotation = rvec

        return stamped_transform

    @staticmethod
    def stamped_transforms_to_matrices(stamped_transforms):
        matrices = []
        for stamped_transform in stamped_transforms:
            translation = stamped_transform.transform.translation
            rotation = stamped_transform.transform.rotation

            translation = np.array([translation.x, translation.y, translation.z])
            rotation = np.array([rotation.x, rotation.y, rotation.z, rotation.w])

            # Construct the transformation matrix
            matrix = tf.transformations.compose_matrix(
                translate=translation,
                angles=tf.transformations.euler_from_quaternion(rotation))

            matrices.append(matrix)

        return matrices

    @staticmethod
    def convert_to_dataframe(sample_transforms):
        # Convert dict of [category, list(stamped_transform)]
        # to panda frame [category,
        # translationX, translationY, translationZ,
        # rotationX, rotationY, rotationZ , rotationW]

        data = []

        for sample_category, poses in sample_transforms.items():
            for r_vec, t_vec in poses:
                r_vec = TypeConverter.matrix_to_quaternion_vector(r_vec)
                if t_vec is not None and r_vec is not None:
                    t_vec = np.array(t_vec).flatten()
                else:
                    t_vec = np.zeros((1, 3)).flatten()
                    r_vec = np.zeros((1, 4)).flatten()
                    r_vec[3] = 1.0

                data.append([
                    sample_category,
                    t_vec[0], t_vec[1], t_vec[2],
                    r_vec[-0], r_vec[1], r_vec[2], r_vec[3]
                ])

        df = pd.DataFrame(data, columns=[
            'Category',
            'Translation X', 'Translation Y', 'Translation Z',
            'Rotation X', 'Rotation Y', 'Rotation Z', 'Rotation W'
        ])
        return df

    @staticmethod
    def estimates_to_transforms(estimates, parent_frame_name):

        methods = ['TSAI', 'PARK', 'HORAUD', 'ANDREFF', 'DANIILIDIS']
        estimate_transforms = []
        for i in range(len(estimates)):
            entry = estimates[i]
            rotation_matrix = entry[0][0]
            quaternions = TypeConverter.matrix_to_quaternion_vector(rotation_matrix)
            translation = entry[0][1]
            transform = TypeConverter.vectors_to_stamped_transform(translation, quaternions, parent_frame_name,
                                                                   f'camera_estimate_{methods[i]}')
            estimate_transforms.append(transform)
        return estimate_transforms
