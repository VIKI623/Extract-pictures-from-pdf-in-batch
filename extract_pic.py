# -*- coding: utf-8 -*-
# @Author  : Zhao Xin
# @Date    : 2020/8/9 23:46
# @Version : Python 3.7.6
# @File    : extract_pic.py

import argparse
import functools
import os

import fitz

# set required picture size for your case!
# unit: pixel
HEIGHT_GREATER_THAN_WIDTH = True
MAX_ID_PHOTO_WIDTH = 900
MAX_ID_PHOTO_HEIGHT = 900
MIN_ID_PHOTO_WIDTH = 150
MIN_ID_PHOTO_HEIGHT = 150
MAX_DIFF_COORDINATE_IN_SAME_LINE = 10


def cmp_coordinates(key0, key1):
    key0 = key0[1]
    key1 = key1[1]
    x0 = key0[0]
    y0 = key0[1]
    x1 = key1[0]
    y1 = key1[1]

    if y0 > y1:
        return 1
    if y0 < y1:
        return -1
    if x0 > x1:
        return 1
    if x0 < x1:
        return -1

    return 0


def map_coordinate_to_index(x0s):
    x_idx = 0
    x0_to_idx = {}

    for idx in range(len(x0s)):
        if idx == 0:
            x0_to_idx[x0s[idx]] = x_idx
            x_idx += 1
        else:
            if x0s[idx] - x0s[idx - 1] > MAX_DIFF_COORDINATE_IN_SAME_LINE:
                x0_to_idx[x0s[idx]] = x_idx
                x_idx += 1
            else:
                x0_to_idx[x0s[idx]] = x_idx - 1

    return x0_to_idx


def extract_pic_from_pdf(pdf_file_dir: str, pdf_file_name: str, output_dir: str, output_name: str) -> bool:
    """
    extract pictures from single pdf file, number the pictures from left to right, up to down

    :param pdf_file_dir: source pdf file directory
    :param pdf_file_name: source pdf file name
    :param output_dir: extracted pictures output directory
    :param output_name: extracted pictures output name
                        (final output name is: output_name_[number].png)
    :return: processed result status (True for success, False for failure)
    """
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    doc = fitz.open(os.path.join(pdf_file_dir, pdf_file_name))

    images_list = []
    for page in doc:
        imglist = page.getImageList(full=True)

        # filter out ID Photo image
        images = []
        for img in imglist:
            # 2:width, 3:height
            if MIN_ID_PHOTO_WIDTH < img[2] < MAX_ID_PHOTO_WIDTH and MIN_ID_PHOTO_HEIGHT < img[3] < MAX_ID_PHOTO_HEIGHT \
                    and (not HEIGHT_GREATER_THAN_WIDTH or img[2] <= img[3]):
                bbox = page.getImageBbox(img)
                image = {'xref': img[0],
                         'coordinates': (bbox.x0, bbox.y0)
                         }
                images.append(image)

        x0s = sorted([img['coordinates'][0] for img in images])
        y0s = sorted([img['coordinates'][1] for img in images])

        x0_to_idx = map_coordinate_to_index(x0s)
        y0_to_idx = map_coordinate_to_index(y0s)

        # sort image according to coordinates
        idx_bboxs = [(x0_to_idx[img['coordinates'][0]], y0_to_idx[img['coordinates'][1]]) for img in images]
        idx_bboxs = sorted(enumerate(idx_bboxs), key=functools.cmp_to_key(cmp_coordinates))
        indices = [ib[0] for ib in idx_bboxs]
        images = [images[i] for i in indices]

        images_list.append(images)

    # output image to output_dir
    file_name = output_name + "_{}.png"
    imgcount = 1
    for images in images_list:
        for image in images:
            pix = fitz.Pixmap(doc, image['xref'])
            pix = fitz.Pixmap(fitz.csRGB, pix)
            pix.writePNG(os.path.join(output_dir, file_name.format(imgcount)))
            imgcount += 1

    if imgcount == 1:
        print("Can not detect required picture: {}.".format(pdf_file_name))
        return False

    return True


def extract_pic_from_pdf_batch(pdf_file_dir: str, output_dir: str) -> None:
    """
    extract pictures from pdf files in batch

    :param pdf_file_dir: source pdf files directory
    :param output_dir: extracted pictures output directory
    :return: None
    """
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    pre_region_code = None
    list_id = 1
    processed_count = 0
    missing_list = []
    for root, dirs, files in os.walk(pdf_file_dir):
        total_count = len(files)
        for file in sorted(files):
            region_code = file.split('.')[0].split('_')[0]
            if region_code != pre_region_code:
                list_id = 1
                pre_region_code = region_code
            output_name = region_code + '_{}'.format(list_id)
            res = extract_pic_from_pdf(root, file, output_dir, output_name)
            if res:
                processed_count += 1
            else:
                missing_list.append(file)
            list_id += 1
    missing_count = total_count - processed_count

    print("Finished! ".format(pdf_file_dir))
    print("Processed pdf file count: {}".format(processed_count))
    print("Not processed pdf file count: {}".format(missing_count))

    if missing_count != 0:
        miss_dir = os.path.join(output_dir, 'missing')
        if not os.path.exists(miss_dir):
            os.mkdir(miss_dir)
        missing_output_path = os.path.join(miss_dir, 'missing_list.txt')
        with open(missing_output_path, mode='w', encoding='utf8') as f:
            for file in missing_list:
                f.write(file + '\n')
        print("miss_list.txt has been output into {}.".format(missing_output_path))

    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_file_dir", type=str, help="source pdf file directory", required=True)
    parser.add_argument("--output_dir", type=str, help="output directory", required=True)
    args = parser.parse_args()

    extract_pic_from_pdf_batch(args.pdf_file_dir, args.output_dir)
