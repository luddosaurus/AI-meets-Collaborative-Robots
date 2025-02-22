import cv2


# Draw stuffs on images
class DaVinci:

    @staticmethod
    def draw_roi_rectangle(image, x, y, roi):
        roi_minus_one = roi - 1
        x1 = x - int(roi_minus_one / 2)
        y1 = y - int(roi_minus_one / 2)
        x2 = x + int(roi_minus_one / 2)
        y2 = y + int(roi_minus_one / 2)
        color = (0, 255, 0)

        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness=1)
        # cv2.circle(image, (x, y), 20, color, thickness=3)

        return image

    @staticmethod
    def resize_and_crop_image(image, width, height):
        # Get the current size of the image
        current_height, current_width = image.shape[:2]
        if current_width == width and current_height == height:
            return image

        return image[:height, :width, :]

        # Calculate the aspect ratio of the image
        aspect_ratio = current_width / current_height

        # Calculate the target aspect ratio
        target_aspect_ratio = width / height

        if aspect_ratio > target_aspect_ratio:
            # Resize the image based on width
            new_width = int(height * aspect_ratio)
            resized_image = cv2.resize(image, (new_width, height))
            # Calculate the crop region
            start = new_width - width

            cropped_image = resized_image[:, :-start]
        else:
            # Resize the image based on height
            new_height = int(width / aspect_ratio)
            resized_image = cv2.resize(image, (width, new_height))
            # Calculate the crop region
            start = new_height - height

            cropped_image = resized_image[:-start, :]

        return cropped_image

    @staticmethod
    def draw_text_box(
            image,
            text,
            position="bottom_left",
            background=(255, 0, 255),
            foreground=(255, 255, 255),
            font_scale=1.0,
            thickness=2,
            box=True,
            margin=40):

        font = cv2.FONT_HERSHEY_SIMPLEX

        # Get the image dimensions
        height, width, _ = image.shape

        # Set the position coordinates based on the input position
        if position == 'top_left':
            x = margin
            y = margin
        elif position == 'top_right':
            x = width - margin
            y = margin
        elif position == 'bottom_left':
            x = margin
            y = height - margin
        elif position == 'bottom_right':
            x = width - margin
            y = height - margin
        else:
            x = width / 2
            y = height / 2

        # Get the text size
        text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

        if box:
            # Calculate the box coordinates
            box_x1 = x
            box_y1 = y - text_size[1] - 20
            box_x2 = x + text_size[0] + 20
            box_y2 = y

            # Draw the rectangle as the box background
            cv2.rectangle(image, (box_x1, box_y1), (box_x2, box_y2), background, -1)

            # Put the text inside the box
            cv2.putText(image, text, (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, font_scale, foreground, thickness,
                        cv2.LINE_AA)

        else:
            # Border

            # Set the outline parameters
            outline_thickness = 3
            outline_color = background
            # Draw the outline text
            for dx in range(-outline_thickness, outline_thickness + 1):
                for dy in range(-outline_thickness, outline_thickness + 1):
                    cv2.putText(image, text, (x + dx, y + dy), font, font_scale, outline_color, thickness)
            # Draw the main text
            cv2.putText(image, text, (x, y), font, font_scale, foreground, thickness)

        return image

    @staticmethod
    def resize(image, target_width=1280):
        height, width = image.shape[:2]
        aspect_ratio = width / height
        target_height = int(target_width / aspect_ratio)
        resized_image = cv2.resize(image, (target_width, target_height))

        return resized_image

    @staticmethod
    def draw_charuco_corner(image, corner):
        cv2.circle(img=image, center=(int(corner[0][0]), int(corner[0][1])), radius=10, color=(255, 255, 0),
                   thickness=-1)
        return image
