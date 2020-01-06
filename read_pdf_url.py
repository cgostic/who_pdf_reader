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
# Cari Gostic, January 2nd, 2020
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

###########################################################
# FUNCTIONS
###########################################################
def find_nth(haystack, needle, n):
    """
    Finds nth occurrence of a string in a piece of text.
    If n is negative, returns nth instance of string from
    the end of the text.

    Parameters
    ----------
    haystack (str): piece of text to search through

    needle (str): string to search for in text

    n (int): which occurence to identify (1st, 2nd, 3rd)

    Returns:
    -------
    int:
        position in haystack where nth occurrence of
        needle starts.
    """
    if n < 0:
        return [match.start(0) for match in re.finditer(needle, haystack)][n]
    else:
        return [match.start(0) for match in re.finditer(needle, haystack)][n-1]

def download_pdf(download_url, folder):
    """
    Downloads pdf from specified url and saves to specified 
    filepath under filename from URL
    
    Parameters
    ----------
    download_url (str): URL of pdf to download

    folder (str): local filepath in which to save pdf 

    Returns
    -------
    file_path (str): path to downloaded file
    """
    response = urllib.request.urlopen(download_url)
    filename = download_url.split('/')[-1]
    file = open(folder+'/'+filename, 'wb')
    file.write(response.read())
    file.close()
    return(folder+'/'+filename)

def delete_pdf(download_url, folder):
    """
    Deletes pdf that was downloaded from URL to
    a local folder

    Parameters
    ----------
    download_url (str): URL that the pdf was downloaded from

    folder (str): filepath where pdf exists locally
    """
    filename = download_url.split('/')[-1]
    os.remove(folder+'/'+filename)

def convert_date(string):
    """
    Converts date string in format dd/mm/yyyy
    to format dd-Mmm-yyyy
    """
    x = string.split('/')
    #print(x)
    try:
        date = datetime.datetime(int(x[2]),int(x[1]),int(x[0]))
        date_str = date.strftime("%d-%b-%Y")
        return(date_str)
    except (IndexError, ValueError) as errors:
        print('Date formats other than dd/mm/yyyy detected in',report_date,'report:',string)
        return(string)
        pass

def detect_report_date(pageObj):
    """Returns report date from header of WHO assessment report"""
    if re.findall('(?<=Summary and assessment).* (\d{1,2} \w* \d\d\d\d).*(?=Since)', pageObj) != []:
        date_header = re.findall('(?<=Summary and assessment).* (\d{1,2} \w* \d\d\d\d).*(?=Since)', pageObj)[0].split(' ')
        report_date = date_header[0]+'-'+date_header[1][:3]+'-'+date_header[2]
    else:
        report_date = 'weird report date detected for '+url
    return(report_date)

def parse_annex_table(num_pages,annex_string, strain, report_date):
    """
    Parses annex table in WHO assessment report into pandas dataframe
    with columns strain, age, sex, date_onset, date_announced, exposure.

    Parameters
    ----------
    num pages (int): The number of pages in the pdf

    annex_string (str): String to search for in table header 
    that denotes the start of the annex table for the strain

    strain (str): flu strain

    report_date (str): The WHO assessment report date (dd-Mmm-yyyy)

    Returns
    -------
    DataFrame Object
        A dataframe with columns: 
        strain, age, sex, date_onset, date_announced, exposure
    """
    # Find pages with annex table
    for i in range(0, num_pages):
        page_i = pdfReader.getPage(i)
        page_text = page_i.extractText()
        if re.search(annex_string,page_text):
            annex_page = i
    if annex_page != num_pages:
        i = str(annex_page)+'-'+str(num_pages)
    # pull relevant information from annex table (age, gender, onset date, poultry exposure)
    while True:
        try:
            print('----Reading data from annex table...')
            df_annex = tabula.read_pdf(file, lattice=True, pages=i)
            cols = [x for x in df_annex.columns if not x.startswith('Pro') and not x.startswith('Case')]
            df_annex = df_annex[cols]
            df_annex.columns = ['age', 'sex', 'date_onset', 'exposure']
            break
        except ValueError:
            print('------Checking if table begins on page after table header...')
            try:
                for i in range(0, num_pages):
                    page_i = pdfReader.getPage(i)
                    page_text = page_i.extractText()
                    if re.search(annex_string,page_text):
                        annex_page = i + 1
                if annex_page != num_pages:
                    i = str(annex_page)+'-'+str(num_pages)
                df_annex = tabula.read_pdf(file, lattice=True, pages=i)
                cols = [x for x in df_annex.columns if not x.startswith('Pro') and not x.startswith('Case')]
                df_annex = df_annex[cols]
                df_annex.columns = ['age', 'sex', 'date_onset', 'exposure']
                break
            except ValueError:
                print('------Could not read in annex table for '+report_date+'...investigate PDF')
                break
    # Add strain and report_date columns
    df_annex['strain'] = strain 
    df_annex['date_announced'] = report_date
    # Make poultry exposure binary (0 for no exposure, 1 for exposure)
    df_annex['exposure'] = df_annex['exposure'].str.replace(r'.*[Pp]oultry.*', '1').str.replace(r'[Nn]o [Kk]nown [Ee]xposure', '0').str.replace(r'.*[Ii]nvestig', 'unknown').str.replace(r'[Oo]ccupational [Ee]xposure', '1').str.replace('[Uu]nknow.*', 'unknown').str.replace('[Nn]o clear exposure', '0')
    # Format onset date
    df_annex['date_onset'] =  df_annex['date_onset'].apply(convert_date)
    # Rearrange columns
    df_annex = df_annex[['strain', 'age', 'sex', 'date_onset', 'date_announced', 'exposure']]
    return(df_annex)

def detect_patient_age(info_par):
    """Returns age of patient described in paragraph of WHO assessment"""
    if re.findall('(\d{1,2}) ?(:?-?(year|month)(-| )old)',info_par) != []:
        age = re.findall('(\d{1,2}) ?(:?-?(year|month)(-| )old)',info_par)[0][0]
    else:
        age = 'unknown'
    return(age)

def detect_onset_date(pageObj,info_par):
    """Returns the illness onset date as described in paragraph of WHO assessment"""
    date_header = re.findall('(?<=Summary and assessment).* (\d{1,2} \w* \d\d\d\d).*(?=Since)', pageObj)[0].split(' ')
    if re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != [] and not report_date.startswith('weird'):
        onset_date_dm = re.findall('(?:[Ss]ymptoms)( (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1].split(' ')
        onset_date = onset_date_dm[0]+'-'+onset_date_dm[1][:3]+'-'+date_header[2]
    elif re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)', info_par) != [] and not report_date.startswith('weird'):
        onset_date_dm = re.findall('(?:[Oo]nset)( (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1].split(' ')
        onset_date = onset_date_dm[0]+'-'+onset_date_dm[1][:3]+'-'+date_header[2]
    elif re.findall('(?:developed (\w* ){0,4})(\d{1,2} \w*)', info_par) != [] and not report_date.startswith('weird'):
        onset_date_dm = re.findall('(?:developed (\w* ){0,4})(\d{1,2} \w*)',info_par)[0][-1].split(' ')
        onset_date = onset_date_dm[0]+'-'+onset_date_dm[1][:3]+'-'+date_header[2]
    else:
        if report_date.startswith('weird'):
            onset_date = 'bad report date'
        else:
            onset_date = 'check onset date format for '+url
    return(onset_date)

def detect_patient_gender(info_par):
    """Returns the age of patient described in WHO assessment"""
    if re.findall('(male|female)', info_par) != []:
        gender = re.findall('(male|female)', info_par)[0][0]
    elif re.findall('( [Hh]e | [Hh]er )', info_par) != []:
        gender = re.findall('( [Hh]e | [Ss]he )', info_par)[0]
        if gender == ' he ' or gender == ' He ':
            gender = 'm'
        else:
            gender = 'f'
    elif re.findall('( [Mm]an | [Ww]oman )', info_par) != []:
        gender = re.findall('( [Mm]an | [Ww]oman )', info_par)[0]
        if gender == ' man ' or gender == ' Man ':
            gender = 'm'
        else:
            gender = 'f'
    else:
        gender = 'Not reported as male/female...Check '+url
    return(gender)

def detect_poultry_exposure(info_par):
    """
    Returns poultry exposure (binary, 0 = no exposure, 1 = exposure) as described
    in WHO assessment report
    """
    if re.findall('(?<=\.)( [A-Za-z ,]* poultry [A-Za-z ,]*)(\.|;)',info_par) != []:
        poul_sentence = re.findall('((?<=\.)( [A-Za-z ,]* poultry [A-Za-z ,]*)(\.|;))',info_par)[0][0]
    elif re.findall('(\w* )*(exposure )(\w* )*', info_par) != []:
        poul_sentence = re.findall('((\w* )*(exposure )(\w* )*)', info_par)[0][0]
    elif re.findall('(\w* )*(birds? )(\w* )*', info_par) != []:
        poul_sentence = re.findall('((\w* )*(birds? )(\w* )*)', info_par)[0][0]
    # Code exposure as binary 1 = exposure, 0 = no exposure
    if not re.search('([Nn]o |not|none)', poul_sentence):
        poultry_exposure = 1
    else:
        poultry_exposure = 0
    return(poultry_exposure)
###########################################################################

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
df_h7n9 = pd.DataFrame(columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'exposure'])
df_h5n1 = pd.DataFrame(columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'exposure'])

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
            df_annex = parse_annex_table(num_pages, annex_string, strain, report_date)
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
                onset_date = detect_onset_date(pageObj[:300], info_par[start_index:next_index])

                # Identify gender
                gender = detect_patient_gender(info_par[start_index:next_index])
                
                # Check for poultry exposure
                poultry_exposure = detect_poultry_exposure(info_par[start_index:next_index])

                # Add values to data frame
                # columns = ['strain', 'onset_date', 'report_date', 'poultry_exposure', 'age' 'gender']
                df_h5n1 = df_h5n1.append(pd.DataFrame([[strain, age, gender, onset_date, report_date, poultry_exposure]], 
                                            columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'exposure']))
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
            df_annex = parse_annex_table(num_pages, annex_string, strain, report_date)
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
                onset_date = detect_onset_date(pageObj[:300], info_par[start_index:next_index])

                # Identify gender
                gender = detect_patient_gender(info_par[start_index:next_index])
                
                # Check for poultry exposure
                poultry_exposure = detect_poultry_exposure(info_par[start_index:next_index])

                # Add values to data frame
                # columns = ['strain', 'onset_date', 'report_date', 'poultry_exposure', 'age' 'gender']
                df_h7n9 = df_h7n9.append(pd.DataFrame([[strain, age, gender, onset_date, report_date, poultry_exposure]], 
                                            columns = ['strain', 'age', 'sex', 'date_onset', 'date_announced', 'exposure']))
                start_index = next_index

    delete_pdf(url, folder_location)
df_h7n9.to_csv('results/WHO-avian-flu-H7N9-reports_2017-present.csv')
df_h5n1.to_csv('results/WHO-avian-flu-H5N1-reports_2017-present.csv')

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
