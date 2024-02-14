import sys
import os
import logging
import hashlib
import shutil
import threading


def synchronizing_files(source, replica):
    try:
        source_file_names = os.listdir(source)
        replica_file_names = os.listdir(replica)
        for source_file_name in source_file_names:
            detected = False
            for replica_file_name in replica_file_names:
                if source_file_name == replica_file_name:
                    detected = True

                    # Creates a variable that contains the path with the file_name
                    path = os.path.join(source, source_file_name)
                    if os.path.isdir(path):
                        logging.info(f"New folder detected \"{source_file_name}\"")
                        synchronizing_files(path, os.path.join(replica, source_file_name))
                        break
                    elif not os.path.isfile(path):
                        logging.error(f"File (\"{source_file_name}\") type not detected.")
                        return

                    source_file_md5 = calculate_md5_file(os.path.join(source, source_file_name))
                    replica_file_md5 = calculate_md5_file(os.path.join(replica, replica_file_name))
                    if source_file_md5 != replica_file_md5:  # Compare the two md5 and if they are different
                        logging.info(f"Synchronizing file \"{source_file_name}\"")
                        sync_file(source, source_file_name, replica)  # Synchronise the file
                    break
            if not detected:
                path = os.path.join(source, source_file_name)
                if os.path.isdir(path):
                    os.mkdir(os.path.join(replica, source_file_name))
                    logging.info(f"New folder created \"{source_file_name}\"")
                    synchronizing_files(path, os.path.join(replica, source_file_name))
                elif os.path.isfile(path):
                    logging.info(f"Adding new file \"{source_file_name}\" to replica \"{replica}\"")
                    sync_file(source, source_file_name, replica)

        # Detect what no longer exists in the source and delete it in the replica
        source_file_names = os.listdir(source)
        replica_file_names = os.listdir(replica)
        for replica_file_name in replica_file_names:  # Check if the replica file exists in the source
            detected = False
            for source_file_name in source_file_names:
                if source_file_name == replica_file_name:
                    detected = True

            if not detected:
                path = os.path.join(replica, replica_file_name)
                if os.path.isdir(path):
                    shutil.rmtree(path)  # Remove the directory and all its contents
                    logging.info(f"Deleted folder \"{replica_file_name}\"")
                elif os.path.isfile(path):
                    logging.info(f"Removed file \"{replica_file_name}\" from replica \"{replica}\"")
                    os.remove(path)
    except Exception as exception:
        logging.error(f"Error synchronizing files: {exception}")


def function_thread(period, stop_event, source, replica):
    while not stop_event.is_set():
        logging.info("Executing periodic task...")
        synchronizing_files(source, replica)
        stop_event.wait(period)


# Synchronize the file from the source folder to destination(replica)
def sync_file(source, file_name, destination):
    source_file_name = os.path.join(source, file_name)
    destination_file_name = os.path.join(destination, file_name)
    shutil.copyfile(source_file_name, destination_file_name)


def calculate_md5_file(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as file:
        for block in iter(lambda: file.read(4096), b""):
            hash_md5.update(block)
    return hash_md5.hexdigest()


arguments = sys.argv[1:]

if len(arguments) != 4:
    print("Missing arguments")
    exit(-1)

source = arguments[0]
replica = arguments[1]
period = int(arguments[2])
log_file_path = arguments[3]

if not os.path.exists(source):
    print("source file does not exist")
    exit(-1)

if not os.path.exists(replica):
    print("replica file does not exist")
    exit(-1)

if not os.path.exists(log_file_path):
    print("log file does not exist")
    exit(-1)

if period <= 0:
    print("period must be greater than 0")

# Configure logging
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,  # Set logging level to INFO
    format='%(asctime)s - %(levelname)s - %(message)s')  # Define log message format

# Create an event to control the periodic execution
stop_event = threading.Event()

# Create thread
thread = threading.Thread(target=function_thread, args=(period, stop_event, source, replica))

try:
    # Start the thread
    thread.start()
    logging.info("Starting thread")

    while thread.is_alive():
        thread.join(0.5)
except KeyboardInterrupt as e:
    logging.info("Ctrl+C detected killing thread...")
    stop_event.set()
    thread.join()
    sys.exit(0)
