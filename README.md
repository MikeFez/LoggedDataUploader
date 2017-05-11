# RaspberryPi Offline Data Logger (For Read Only Filesystems)
I have a project that requires the periodic recording of data (in this case, timestamped temperature data from multiple sensors). This same project also requires the Unix filesystem to be read only in order to prevent filesystem corruption in the case of an unexpected shutdown, which happens frequently.

Rather than mount another storage device, I opted to have the data upload directly to my server via SFTP when internet is available (I preconfigured various networks for the RPi to connect to).

The way it works is as follows:
	- Collect timestamped data point
	- Wait 30 seconds (configurable)
	- Repeat for 5 minutes (configurable)
	- Check for internet
		- If not connected, collect data for another 5 minutes
	- If connected, attempt to download previously uploaded data points to temporary storage
	- If previous data exists, append the newly collected data to it. Otherwise, save current data to temporary storage
	- Upload data, wipe temporary storage
  
# Note
This script uses Prowl (https://www.prowlapp.com/) in order to notify me upon script launch, data upload, and in the event of an error that crashes the program.
