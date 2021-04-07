import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from datetime import datetime as dt
import os, glob, sys
import shutil
import requests
import zipfile
import warnings
import logging

warnings.filterwarnings("ignore")
import yaml
from config import user, passwd

stream = open("settings.yml", "r")
settings_param = yaml.load(stream)
# logfile = open(settings_param["logfileName"], "w")

if os.path.exists(settings_param["logfileName"]):
    os.remove(settings_param["logfileName"])
logging.basicConfig(
    filename=settings_param["logfileName"],
    level=logging.INFO,
    format="%(asctime)s|--> %(name)s| %(levelname)s| %(message)s",
)


dataformat = settings_param["dataformat"]
starttime = settings_param["starttime"]
endtime = settings_param["endtime"]

logging.info("Requesting data from {} to {}".format(starttime, endtime))


# Data location
datadir = "./downloadDir"


def page_is_loaded(br):
    return br.find_element_by_tag_name("body") != None


## all available Fnet stations
fnet = pd.read_csv(
    "F_net_stations.txt",
    delimiter="\s+",
    header=None,
    names=["Station", "stn", "Lat", "Lon", "Alt", "tt1", "tt2", "tt3"],
)
nfnet = fnet.iloc[::2, 0:5]
nfnet.set_index("Station", inplace=True)


if settings_param["stationList"].upper() == "ALL":
    stations_to_request = nfnet["stn"].values
else:
    stations_to_request = settings_param["stations"]

comps = settings_param["components"]  # ["BHZ", "BHN", "BHE"]
for i, ss in enumerate(stations_to_request):
    i += 1

    for j in range(len(comps)):
        try:
            # request data for last one day
            command1 = "get {} {} {} {}".format(ss, comps[j], starttime, endtime)
            # get ABU BHZ 2000/01/01,00:00:00 2000/01/01,00:10:00

            logging.info(
                "Working on File {}/{}, Station: {}, Component: {}".format(
                    i, len(stations_to_request), ss, comps[j]
                )
            )

            # open up firefox browser and navigate to web page
            br = (
                webdriver.Firefox()
            )  # or webdriver.Chrome() but needs chromedriver or geockodriver
            br.get(
                "https://{}:{}@www.fnet.bosai.go.jp/auth/dataget/?LANG=en".format(
                    user, passwd
                )
            )
            timeout = 20  # wait for 20 sec to load
            try:
                wait = WebDriverWait(br, timeout)
                wait.until(page_is_loaded)
            except TimeoutException:
                logging.error("The requested web page is taking long to load!")
                br.quit()
            assert (
                "Retrieval of Waveforms" in br.title
            )  # look for the title on the page
            if dataformat.upper() == "MSEED":
                br.find_element_by_xpath(
                    "/html/body/form/table[1]/tbody/tr[3]/td/ul[1]/fieldset/label[1]"
                ).click()  # select data format MSEED
            elif dataformat.upper() == "SAC":
                br.find_element_by_xpath(
                    "/html/body/form/table[1]/tbody/tr[3]/td/ul[1]/fieldset/label[3]"
                ).click()  # select data format SAC
            elif dataformat.upper() == "TEXT":
                br.find_element_by_xpath(
                    "/html/body/form/table[1]/tbody/tr[3]/td/ul[1]/fieldset/label[4]"
                ).click()  # select data format SAC

            # br.find_element_by_xpath("/html/body/form/table[1]/tbody/tr[3]/td/ul[2]/fieldset/label[5]").click() #select data output zip

            ## find the command text area
            elem = br.find_element_by_name("commands")
            elem.clear()  # clear the previously written
            logging.info(f"Command: {command1}")
            elem.send_keys(command1)

            br.find_element_by_xpath(
                "/html/body/form/table[1]/tbody/tr[3]/td/div[8]/button"
            ).click()

            try:
                # wait to make sure there are two windows open
                WebDriverWait(br, 10).until(lambda d: len(d.window_handles) == 2)

                # switch windows
                br.switch_to_window(br.window_handles[1])

                element = WebDriverWait(br, 40).until(
                    EC.element_to_be_clickable((By.XPATH, "/html/body/a[1]"))
                )
                linktosave = element.get_attribute("href")
                filename = linktosave.split("=")[1]
                fileFormat = ".mseed"
                fullfilename = os.path.join(datadir, filename)

                response = requests.get(linktosave, stream=True, auth=(user, passwd))
                with open(fullfilename, "wb") as out_file:
                    shutil.copyfileobj(response.raw, out_file)
                del response
                # element.click()
                zip_ref = zipfile.ZipFile(fullfilename, "r")
                tmplistname = zip_ref.namelist()
                zip_ref.extractall(datadir)
                zip_ref.close()
                os.remove(fullfilename)
                extractFileName = datadir + "/" + tmplistname[0]
                if os.path.exists(extractFileName):
                    os.rename(extractFileName, extractFileName + ".mseed")
                    logging.info(
                        "Successful download: {}\n".format(
                            os.path.basename(extractFileName) + ".mseed"
                        )
                    )
            except Exception as e:
                logging.error(
                    "TIMEOUT: Loading file is taking way too long for file {}, station {}, component {}!".format(
                        ss, comps[j]
                    )
                )
                logging.error(f"Failed download: {e}\n")

            logging.info(f"Data URL: {br.current_url}")
            br.quit()
        except Exception as err:
            logging.error(f"{err}\n")
            print(sys.exc_info())

