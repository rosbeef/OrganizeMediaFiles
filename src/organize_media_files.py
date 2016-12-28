# -*- coding: utf-8 -*-

"""
Organize pictures file into directory tree with year and month.
Use perl exiftool to get creation date and filename from file metadata.

Strongly inspired from the project:
    https://github.com/OneLogicalMyth/Random-Scripts.git

Created on 27/12/16 15:53

@author: vpistis
"""
import datetime
import filecmp
import json
import os
import shutil
import subprocess
import sys
import timeit

BASE_DIR = str(os.path.dirname(__file__))

with open(BASE_DIR + "/config.json") as f:
    config_json = json.loads(f.read())


def get_setting(key, config=config_json):
    """Get the secret variable or return explicit exception."""
    try:
        return config[key]
    except KeyError:
        error_msg = "Set the {0} environment variable".format(key)
        raise Exception(error_msg)


def which(program):
    """
    Check if a program/executable exists

    :param program:
    :return:
    """

    def is_exe(f_path):
        return os.path.isfile(f_path) and os.access(f_path, os.X_OK)

    fpath, fname = os.path.split(program)

    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


class Logger(object):
    """
    http://stackoverflow.com/a/14906787/5941790
    """

    def __init__(self):
        self.terminal = sys.stdout
        self.log = open(get_setting("LOG_FILE"), "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass


sys.stdout = Logger()

PROCESS_IMAGES = get_setting("PROCESS_IMAGES")
PROCESS_VIDEOS = get_setting("PROCESS_VIDEOS")

IMAGES_SOURCE_PATH = get_setting("IMAGES_SOURCE_PATH")
IMAGES_DESTINATION_PATH = get_setting("IMAGES_DESTINATION_PATH")
IMAGE_FILES_EXTENSIONS = tuple(get_setting("IMAGE_FILES_EXTENSIONS"))
IMAGE_FILENAME_SUFFIX = get_setting("IMAGE_FILENAME_SUFFIX")

VIDEOS_SOURCE_PATH = get_setting("VIDEOS_SOURCE_PATH")
VIDEOS_DESTINATION_PATH = get_setting("VIDEOS_DESTINATION_PATH")
VIDEO_FILES_EXTENSIONS = tuple(get_setting("VIDEO_FILES_EXTENSIONS"))
VIDEO_FILENAME_SUFFIX = get_setting("VIDEO_FILENAME_SUFFIX")

# If false copy file and don't remove old file
REMOVE_OLD_FILES = get_setting("REMOVE_OLD_FILES")

APPEND_ORIG_FILENAME = get_setting("APPEND_ORIG_FILENAME")
# process only files with this extensions


DATE_FORMAT_OUTPUT = get_setting("DATE_FORMAT_OUTPUT")

# in case you use nextcloud or owncloud, set NEXTCLOUD=True to rescan all files
NEXTCLOUD = get_setting("NEXTCLOUD")
NEXTCLOUD_PATH = get_setting("NEXTCLOUD_PATH")
NEXTCLOUD_USER = get_setting("NEXTCLOUD_USER")


def get_create_date(filename):
    """
    Get creation date from file metadata

    :param filename:
    :return:
    """
    # Read file
    # open_file = open(filename, 'rb')
    command = ["exiftool", "-CreateDate", "-s3", "-fast2", filename]
    metadata = subprocess.check_output(command)

    try:
        # Grab date taken
        datetaken_object = datetime.datetime.strptime(metadata.rstrip(), "%Y:%m:%d %H:%M:%S")

        # Date
        day = str(datetaken_object.day).zfill(2)
        month = str(datetaken_object.month).zfill(2)
        year = str(datetaken_object.year)

        # New Filename
        output = [day, month, year, datetaken_object.strftime(DATE_FORMAT_OUTPUT)]
        return output

    except Exception as e:
        print("{}".format(e))
        print("exiftool is installed?")
        return None


def get_file_name(filename):
    """
    Get real filename from metadata

    :param filename:
    :return:
    """
    try:
        command = ["exiftool", "-filename", "-s3", "-fast2", filename]
        metadata = subprocess.check_output(command)
        return metadata.rstrip()
    except Exception as e:
        print("{}".format(e))
        print("exiftool is installed?")
        return None


def get_file_ext(filename):
    """
    Return the file extension based on file name from metadata, include point.
    Example return: '.jpg'

    :param filename:
    :return:
    """
    extension = ".{}".format(get_file_name(filename).split(".")[-1])
    return extension


def organize_files(src_path, dest_path, files_extensions, filename_suffix=""):
    """
    Get all files from directory and process

    :return:
    """
    _src_path = src_path
    _dest_path = dest_path
    _files_extensions = files_extensions
    _filename_suffix = filename_suffix

    # check if destination path is existing create if not
    if not os.path.exists(_dest_path):
        os.makedirs(_dest_path)
        print("Destination path created: {}".format(_dest_path))

    if len(os.listdir(_src_path)) <= 0:
        print("No files in path: {}".format(_src_path))
        return 0, 0, 0
    else:
        num_files_processed = 0
        num_files_removed = 0
        num_files_copied = 0

        for file in os.listdir(_src_path):
            if file.lower().endswith(_files_extensions):

                num_files_processed += 1

                filename = _src_path + os.sep + file
                file_ext = get_file_ext(filename)
                dateinfo = get_create_date(filename)

                try:
                    out_filepath = _dest_path + os.sep + dateinfo[2] + os.sep + dateinfo[1]
                    if APPEND_ORIG_FILENAME:
                        out_filename = out_filepath + os.sep + _filename_suffix + dateinfo[3] + '_' + file
                    else:
                        out_filename = out_filepath + os.sep + _filename_suffix + dateinfo[3] + file_ext

                    # check if destination path is existing create if not
                    if not os.path.exists(out_filepath):
                        os.makedirs(out_filepath)

                    # don't overwrite files if the name is the same
                    if os.path.exists(out_filename):
                        # new dest path but old filename
                        out_filename = out_filepath + os.sep + file
                        if os.path.exists(out_filename):
                            shutil.copy2(filename, out_filename + '_duplicate')
                            if filecmp.cmp(filename, out_filename + '_duplicate'):
                                # the old file name exists...skip file
                                os.remove(out_filename + '_duplicate')
                                print("Skipped file: {}".format(filename))
                                continue

                    # copy the file to the organised structure
                    shutil.copy2(filename, out_filename)
                    if filecmp.cmp(filename, out_filename):
                        num_files_copied += 1
                        print('File copied with success to {}'.format(out_filename))
                        if REMOVE_OLD_FILES:
                            os.remove(filename)
                            num_files_removed += 1
                            print('Removed old file {}'.format(filename))
                    else:
                        print('File failed to copy :( {}'.format(filename))

                except Exception as e:
                    print("{}".format(e))
                    print("Exception occurred")
                    return num_files_processed, num_files_removed, num_files_copied
                except None:
                    print('File has no metadata skipped {}'.format(filename))
    return num_files_processed, num_files_removed, num_files_copied


# Nextcloud initiate a scan
def nextcloud_files_scan():
    if NEXTCLOUD:
        try:
            subprocess.Popen("sudo -u {} php {}/console.php files:scan --all".format(NEXTCLOUD_USER, NEXTCLOUD_PATH),
                             shell=True, stdout=subprocess.PIPE)
        except Exception as e:
            print("{}".format(e))
            print("Exception occurred")
    return


def main():
    # check if exiftool is installed
    if not which("exiftool"):
        print("Please...install exiftool first")
        return

    print("======== {} =======".format(datetime.datetime.now()))
    if PROCESS_IMAGES:
        print("Start process images...")
        start_time = timeit.default_timer()
        processed, removed, copied = organize_files(IMAGES_SOURCE_PATH, IMAGES_DESTINATION_PATH,
                                                    IMAGE_FILES_EXTENSIONS, IMAGE_FILENAME_SUFFIX)
        elapsed = timeit.default_timer() - start_time
        print("End process images in: {}".format(elapsed))
        print("Proccessed: {} image files. Removed {} image files. Copied {} image files.".format(processed,
                                                                                                  removed, copied))
    if PROCESS_VIDEOS:
        print("Start process videos...")
        start_time = timeit.default_timer()
        processed, removed, copied = organize_files(VIDEOS_SOURCE_PATH, VIDEOS_DESTINATION_PATH,
                                                    VIDEO_FILES_EXTENSIONS, VIDEO_FILENAME_SUFFIX)
        elapsed = timeit.default_timer() - start_time
        print("End process videos in: {}".format(elapsed))
        print("Proccessed: {} video files. Removed {} video files. Copied {} video files".format(processed,
                                                                                                 removed, copied))

    return


# Execution
main()
nextcloud_files_scan()
