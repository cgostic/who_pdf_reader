# WHO_pdf_reader


The World Health Organization (WHO) outputs [Monthly Risk Assessment Reports](https://www.who.int/influenza/human_animal_interface/HAI_Risk_Assessment/en/) in pdf format that describe new instances of the influenza virus at the human-animal interface. This code loops through each report from January, 2017 to the present and extracts the age, gender, onset-date, report-date, and poultry exposure for each reported case of avian influenza strains (H7N9, H5N1). The following csv's are output in the results folder:

- WHO-avian-flu-H5N1-reports_2017-present.csv
- WHO-avian-flu-H7N9-reports_2017-present.csv

This code was written to contribute to a post-doctoral project by Katie Gostic, PHD (University of Chicago) that aims to model the incidence and spread of the avian flu.

- If you are interested in only the csv output, see the results folder for data ranging from January, 2017 - November, 2019 (the most recent report as of posting, January 4, 2020).
- If a more recent report is available that you would like to include or you'd like to run the code on your own:

# Instructions for running code:

There are two version of the main script, (1) read_pdf_url_docker.py, which has absolute filepaths hard-coded to run successfully within the `carigostic/who_pdf_reader` Docker image, and (2) read_pdf_url.py, which has relative filepaths so to code can run locally.

### Using docker

- Download [Docker](https://www.docker.com/products/docker-desktop) if not already installed
- Download/clone this repository
- Input local **absolute** path to this repository as indicated in code below and execute the following script in the terminal (Linux):

```
sudo docker run --rm -v <absolute local path>/who_pdf_reader:/who_pdf_reader carigostic/who_pdf_reader:v1.0 python /who_pdf_reader/read_pdf_url_docker.py 
```

- View the results folder for csv output

### Manually

- Ensure all package dependencies are met (below), including Java version
- Download/clone this repository
- Navigate to the repository in terminal
- Execute the following script in the terminal (Linux):

```
python read_pdf_url.py` 
```

- View the results folder for csv output

#### This code requires Python 3.7 and the following packages:
- re
- pandas
- PyPDF2 == 1.26.0
- tabula-py == 1.4.3
  - **tabula requires java version 1.8.0 or greater.**
    - Linux/Mac users can check Java version via the terminal (`java -version` for linux users)
    - Windows users may need to set a path to the Java installation
      - See step 2 of https://aegis4048.github.io/parse-pdf-files-while-retaining-structure-with-tabula-py
- urllib
- bs4 == 0.0.1
- os
- datetime


**NOTE: testing has not been confirmed past January, 2017 and oddities/inconsistencies in the wording of the reports may result in errors**

To increase the range of data gathered beyond January, 2017, replace the link to the January, 2017 report in line 270 (shown below) with a link to the earliest report you'd like included. 
```
index_2017 = url_list.index('https://www.who.int/influenza/human_animal_interface/Influenza_Summary_IRA_HA_interface_01_16_2017_FINAL.pdf')+1
```
To include all reports listed on the WHO website, remove the slicing of `url_list` from the for-loop on line 281.



