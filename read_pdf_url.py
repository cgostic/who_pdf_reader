# Parses data from WHO monthly risk assessments on Avian flu 
# strains (H5N1, H7N9) into csv's for further analysis
#
# - Locates risk assessment reports (pdf format) from Jan, 2017 onward
#       - https://www.who.int/influenza/human_animal_interface/HAI_Risk_Assessment/en/,
# - Downloads 1 report at a time to temp folder, extracts data, then deletes
#       the download to minimize memory use.
# - Exports extracted data as csv's to results folder
#       - H5N1 report
#       - H7N9 report
#
# See "Sources" section at bottom of code
#
# Cari Gostic, updated February 18th, 2020
# cari.gostic@gmail.com

import re
import pandas as pd
# Requires PyPDF2
import PyPDF2
# tabula requires java version 1.8.0 or greater. 
# Linux/Mac users can check Java version via the terminal ('java -version' for linux users)
# Windows users may need to set a path to the Java installation
    # See step 2 of https://aegis4048.github.io/parse-pdf-files-while-retaining-structure-with-tabula-py
import tabula
from urllib import request
from bs4 import BeautifulSoup
import os
import urllib
import datetime
import sys

# Import helper functions from src/parse_functions.py
cwd = os.getcwd()
sys.path.append(cwd+'src')
from parse_functions import (find_nth, download_pdf, delete_pdf, 
    month_to_int, detect_poultry_exposure, detect_report_date, parse_annex_table, 
    detect_patient_age, detect_patient_gender, detect_onset_date, bad_dates_rep,
    bad_dates_for)

# connect to WHO website and get list of all pdfs
url="https://www.who.int/influenza/human_animal_interface/HAI_Risk_Assessment/en/"
response = request.urlopen(url).read()
soup= BeautifulSoup(response, "html.parser")     
links = soup.find_all('a', href=re.compile(r'(.pdf)'))

# clean the pdf link names
url_list = []
for link in links:
    if(link['href'].startswith('http')):
        url_list.append(link['href'])
    else:
        url_list.append("https://www.who.int" + link['href'])

# Locate only reports from 2017 onward
index_2017 = url_list.index('https://www.who.int/influenza/human_animal_interface/Influenza_Summary_IRA_HA_interface_01_16_2017_FINAL.pdf')+1
print(str(len(url_list[:index_2017])), 'pdfs located')
# Create temp folder to hold pdfs (one at a time)
folder_location = os.getcwd() + '/tmp_pdfs'
if not os.path.exists(folder_location):os.mkdir(folder_location)

# Create DFs to record data in (will be exported as csv's)
df_h7n9 = pd.DataFrame(columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'poultry_exposure', 'sick_human_exposure'])
df_h5n1 = pd.DataFrame(columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'poultry_exposure', 'sick_human_exposure'])

# Identify pdfs froom 2017 onward on WHO website
for url in url_list[:index_2017]:
    file = download_pdf(url, folder_location)  
    pdfFileObj = open(file, 'rb')
    # pdf reader object
    pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
    # number of pages in pdf
    num_pages = pdfReader.numPages
    # extract all text to string
    pageObj = ''
    for i in range(num_pages):
        pageObj = pageObj + pdfReader.getPage(i).extractText()
    pageObj = pageObj.replace('\n', '')

    # Find report date
    report_date = detect_report_date(pageObj[:300])

    # New infections header string
    ni_header = pageObj[pageObj.find('New infections'):pageObj.find('Risk assessment')]
    # Check for "no new human infections"
    if re.search(r'[Nn]o new human infection', ni_header):
        print('No new cases in',report_date,'report')

    # Check for H5N1 or H7N9 infections
    if not re.search('H5N1', ni_header) and not re.search('H7N9', ni_header):
        print('No cases of H5N1 or H7N9 in',report_date,'report')

    # Check for H5N1 infections
    if re.search('H5N1', ni_header):
        strain = 'H5N1'
        report_date = report_date
        # Identify paragraph with information on H7N9 infections
        info_start = find_nth(pageObj, '[Aa]vian [Ii]nfluenza A\(H5\) viruse?s?', 1)
        info_par = pageObj[info_start:info_start + find_nth(pageObj[info_start:], 
                                'Risk [Aa]ssessment', 1)].replace('\n', '')
        # Print number of cases
        if re.findall('\w*(?= laboratory-confirmed)', info_par)[0] == 'new':
                num_case = re.findall('\w*(?= new laboratory-confirmed)', info_par)[0].replace(' ', '')
        else:
            num_case = re.findall('\w*(?= laboratory-confirmed)', info_par)[0].replace(' ', '')
        # If reported number is string, convert to integer
        if num_case == 'one':
            num_case = 1
        elif num_case == 'two':
            num_case = 2
        elif num_case == 'three':
            num_case = 3
        elif num_case == 'four':
            num_case = 4
        elif num_case == 'five':
            num_case = 5
        elif num_case == 'six':
            num_case = 6 
        print(num_case,'new case(s) of H5N1 detected in',report_date)

        # If annex table exists, extract relevant information to DF
        if re.findall('[Aa]nnex', info_par) != []:
            print('Annex detected for H5N1 cases in',report_date)
            annex_string = "Annex:[\w* \n:-]*A\(H5.*\)"
            df_annex = parse_annex_table(num_pages, annex_string, strain, report_date, pdfReader, file)
            df_h5n1 = df_h5n1.append(df_annex)
        
        # If no annex table exists, extract information from paragraph
        # describing H5N1 cases
        else:
            # Account for multiple cases described by looping through # of
            # ages reported in paragraph
            start_index = 0
            for case in range(num_case):
                # Identify patient age -- if multiple cases, set range to search for only current case
                age = detect_patient_age(info_par[start_index:])
                if num_case > case+1 and re.findall('(\d{1,2})(:?-?(year|month)(-| )old)',info_par[start_index:]) != []:
                        next_index = find_nth(info_par, '(:?-?(year|month)(-| )old)',case+2)-3
                else:
                    next_index = len(info_par)

                # Identify date of illness onset
                onset_date = detect_onset_date(pageObj[:300], info_par[start_index:next_index], report_date)

                # Identify gender
                gender = detect_patient_gender(info_par[start_index:next_index])
                
                # Check for poultry exposure
                poultry_exposure = detect_poultry_exposure(info_par[start_index:next_index])[0]

                # Check for exposure to sick humans
                sick_human_exposure = detect_poultry_exposure(info_par[start_index:next_index])[1]

                # Add values to data frame
                df_h5n1 = df_h5n1.append(pd.DataFrame([[strain, age, gender, onset_date, report_date, poultry_exposure, sick_human_exposure]], 
                                            columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'poultry_exposure', 'sick_human_exposure']))
                start_index = next_index      


    # Check for H7N9 infections
    if re.search('H7N9', ni_header):
        strain = 'H7N9'
        report_date = report_date
        # Identify paragraph with information on H7N9 infections
        info_start = find_nth(pageObj, 'Avian [Ii]nfluenza A\(H7N9\)', 1)
        info_par = pageObj[info_start:info_start + find_nth(pageObj[info_start:], 
                                'Risk [Aa]ssessment', 1)].replace('\n', '')
        # Print number of cases
        if re.findall('\w*(?= laboratory-confirmed)', info_par)[0] == 'new':
                num_case = re.findall('\w*(?= new laboratory-confirmed)', info_par)[0].replace(' ', '')
        else:
            num_case = re.findall('\w*(?= laboratory-confirmed)', info_par)[0].replace(' ', '')
        # If reported number is string, convert to integer
        if num_case == 'one':
            num_case = 1
        elif num_case == 'two':
            num_case = 2
        elif num_case == 'three':
            num_case = 3
        elif num_case == 'four':
            num_case = 4
        elif num_case == 'five':
            num_case = 5
        print(num_case,'new case(s) of H7N9 detected for',report_date)

        # If annex table exists, extract relevant information to DF
        if re.findall('[Aa]nnex', info_par) != []:
            print('--Annex detected for H7N9 cases in',report_date)
            annex_string = "Annex:[\w* \n:-]*A\(H7N9\)"
            df_annex = parse_annex_table(num_pages, annex_string, strain, report_date, pdfReader, file)
            df_h7n9 = df_h7n9.append(df_annex)

        # If no annex table exists, extract information from paragraph
        # describing H7N9 cases
        else: 

            # Account for multiple cases described by looping through # of
            # ages reported in paragraph
            start_index = 0
            for case in range(num_case):
                # Identify patient age -- if multiple cases, set range to search for only current case
                age = detect_patient_age(info_par[start_index:])
                if num_case > case+1 and re.findall('(\d{1,2})(:?-?(year|month)(-| )old)',info_par[start_index:]) != []:
                        next_index = find_nth(info_par, '(:?-?(year|month)(-| )old)',case+2)-3
                else:
                    next_index = len(info_par)

                # Identify date of illness onset
                onset_date = detect_onset_date(pageObj[:300], info_par[start_index:next_index], report_date)

                # Identify gender
                gender = detect_patient_gender(info_par[start_index:next_index])
                
                # Check for poultry exposure
                poultry_exposure = detect_poultry_exposure(info_par[start_index:next_index])[0]

                # Check for exposure to sick humans
                sick_human_exposure = detect_poultry_exposure(info_par[start_index:next_index])[1]

                # Add values to data frame
                df_h7n9 = df_h7n9.append(pd.DataFrame([[strain, age, gender, onset_date, report_date, poultry_exposure, sick_human_exposure]], 
                                            columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'poultry_exposure', 'sick_human_exposure']))
                start_index = next_index

    delete_pdf(url, folder_location)

df_h7n9.to_csv('results/WHO-avian-flu-H7N9-reports_2017-present.csv')
df_h5n1.to_csv('results/WHO-avian-flu-H5N1-reports_2017-present.csv')

print()
print('Date formats other than dd/mm/yyyy detected in:')
print('Report date | Date detected')
for key,value in zip(bad_dates_rep, bad_dates_for):
    print('{:11} | {:8}'.format(key, value))
print('Manual adjustment to above needed in csv files')
print()
print('View generated csv files in the results folder!')


# Delete temp folder
os.removedirs('tmp_pdfs')

# Sources:
    # Read PDF Table
    # https://stackoverflow.com/questions/12571905/finding-on-which-page-a-search-string-is-located-in-a-pdf-document-using-python
    # https://aegis4048.github.io/parse-pdf-files-while-retaining-structure-with-tabula-py

    # Make folder 
    # https://stackoverflow.com/questions/54616638/download-all-pdf-files-from-a-website-using-python

    # Delete folder
    # https://www.dummies.com/programming/python/how-to-delete-a-file-in-python/

    # Download PDF 
    # https://stackoverflow.com/questions/24844729/download-pdf-using-urllib 
    # https://stackoverflow.com/questions/9751197/opening-pdf-urls-with-pypdf
