#!/usr/bin/python3
import requests
import pickle
import os
import sys
from datetime import datetime
from time import sleep
import pysftp
import traceback
import socket

version = "0.1"

data_points = []
event_log = []

# determine system to allow for testing when not running live
running_on_pi = sys.platform.startswith('linux')
if running_on_pi:
    tmp_dir = "/tmp/"
    upload_timeout_mins = 5
else:
    tmp_dir = "tmp/"
    upload_timeout_mins = 1


sftp_data_dir = "REMOTE/PATH/TO/UPLOAD/DATA"
sftp_data_host = "XXXXXXXXXX"
sftp_data_username = "XXXXXXXXXX"
sftp_data_password = "XXXXXXXXXX"


def main():
    global data_points
    while True:
        for x in range(0, upload_timeout_mins * 2):
            # Get data and add to master list
            latest_data = collect_data()
            data_points.append(latest_data)
            # Sort and format latest temps to txt, then add to log
            update_log(str(latest_data))
            print("\tAttempting to upload data in " + str(upload_timeout_mins - (x / 2)) + " minutes")
            sleep(30) if running_on_pi else sleep(5)

        # After 5 minutes of logging every 30s, check if internet is connected and send data if so
        if internet_is_connected():
            update_log("Internet is connected - attempting to upload data")
            try:
                upload_data_sftp()
            except:
                update_log("Error uploading data - attempting upload again in " + str(upload_timeout_mins) + " minutes")
        else:
            update_log("Internet is not connected - attempting upload data in " + str(upload_timeout_mins) + " minutes")


def get_current_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "UNKNOWN"
    return local_ip


def collect_data():
    data_dict = {'time': datetime.now()}
    if running_on_pi:
        # Collect data and organize dict however you like
        pass
    else:
        # Provide fake data, organize dict however you like
        pass
    return data_dict


def internet_is_connected():
    url = "http://www.google.com"
    timeout = 5
    try:
        _ = requests.get(url, timeout=timeout)
        return True
    except:
        print("No internet connection available.")
    return False


def upload_data_sftp():
    current_date = date_filename()

    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    srv = pysftp.Connection(
        host=sftp_data_host,
        username=sftp_data_username,
        password=sftp_data_password,
        cnopts=cnopts
    )

    current_data_points_file = "data_points_%s.list" % current_date
    current_event_log_file = "event_log_%s.txt" % current_date

    new_data = False
    os.chdir(tmp_dir)
    if srv.exists(sftp_data_dir + current_data_points_file):
        update_log("Downloading remote data points")
        srv.get(sftp_data_dir + current_data_points_file)
        new_data = True
    else:
        update_log("Remote data points do not exist")
    if srv.exists(sftp_data_dir + current_event_log_file):
        update_log("Downloading remote event log")
        srv.get(sftp_data_dir + current_event_log_file)
        new_data = True
    else:
        update_log("Remote event log does not exist")

    # Combine Dowloaded & Current Data
    if new_data:
        update_log("Appending new data to remote data")
    else:
        update_log("Saving data for upload")
    append_local_to_remote(current_data_points_file, current_event_log_file)

    update_log("Attempting to upload data")
    if running_on_pi:
        with srv.cd(sftp_data_dir):
            srv.put(tmp_dir + current_data_points_file)
            srv.put(tmp_dir + current_event_log_file)
        notify_prowl('Data Uploaded at ' + datetime.now().strftime('%m/%d/%Y %H:%M:%S'), "Temperature Data Uploaded",
                     True)
    else:
        print("Skipping Data Upload")
    reset_data(current_data_points_file, current_event_log_file)
    srv.close()
    return


def append_local_to_remote(data_points_name, event_log_name):
    # Load Existing or Create New
    if os.path.isfile(tmp_dir + data_points_name):
        with open(tmp_dir + data_points_name, "rb") as temp_file:
            loaded_data_points = pickle.load(temp_file)
    else:
        loaded_data_points = []
    if os.path.isfile(tmp_dir + event_log_name):
        with open(tmp_dir + event_log_name, "r") as event_file:
            loaded_event_log = event_file.read()
    else:
        loaded_event_log = ""

    # Combine Data
    global data_points, event_log
    combined_data_points = loaded_data_points + data_points
    combined_event_log = loaded_event_log + event_log_to_str()

    # Save Combined
    with open(tmp_dir + data_points_name, "wb+") as temp_file:
        pickle.dump(combined_data_points, temp_file)
    with open(tmp_dir + event_log_name, "w+") as event_file:
        event_file.write(combined_event_log)
    return


def update_log(data):
    time = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    global event_log
    event_log.append({'time': time, "data": data})
    print(time, "\t", data)
    return


def event_log_to_str():
    global event_log
    text = ""
    for item in event_log:
        text += item['time'] + "\t" + item['data'] + "\n"
    return text


def reset_data(current_data_points_file, current_event_log_file):
    global data_points, event_log
    data_points = []
    event_log = []
    data_points_location = tmp_dir + current_data_points_file
    event_log_location = tmp_dir + current_event_log_file
    if os.path.isfile(data_points_location):
        os.remove(data_points_location)
    if os.path.isfile(event_log_location):
        os.remove(event_log_location)
    return


def date_filename():
    # 1/15/2017 -> 2017_01.15
    split_date = datetime.now().strftime('%m/%d/%Y').split("/")
    return split_date[2] + "_" + split_date[0] + "." + split_date[1]


def notify_prowl(subject, text, url_enabled):
    update_log(subject)
    prowl_url = "https://api.prowlapp.com/publicapi/add"
    payload = {
        "apikey": "XXXXXXXXXXXXXXXXXXXX",
        "url": "XXXXXXXXXXXXXXXXXXXX",
        "application": "XXXXXXXXXXXXXXXXXXXX",
        "event": subject,
        "description": text
    }
    if not url_enabled:
        del payload['url']
    if running_on_pi:
        try:
            temp = requests.post(prowl_url, data=payload)
            temp.raise_for_status()
        except:
            update_log("Unable to send Prowl notification. Error: " + str(sys.exc_info()[0]))
    else:
        print("\n" + "Prowl Notification:\n" + subject + "\n" + text + "\nURL: " + str(url_enabled) + "\n")
    return


if __name__ == "__main__":
    try:
        if internet_is_connected():
            notify_prowl('Powered on at ' + datetime.now().strftime('%m/%d/%Y %H:%M:%S'),
                         "Version: " + version + "\nLocal IP: " + get_current_ip(), False)
        main()
    except Exception as e:
        notify_prowl("Script Error", str(traceback.format_exc()), False)
